"""Barkod Logo serializer'ları.

PNG dosya doğrulama (yükleme endpoint'inde) ve CRUD serializer burada tanımlıdır.
"""
import struct
import zlib

from rest_framework import serializers

from .models import BarkodLogo


# ─────────────────────────────────────────────────────────────────────────────
# PNG Doğrulama — stdlib (struct + zlib). Pillow gerektirmez.
# Kontroller: magic, max 336×336, ≤1 MB, şeffaf piksel yok.
# ─────────────────────────────────────────────────────────────────────────────

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_PNG_MAX_BYTES = 1 * 1024 * 1024
_PNG_MAX_W = 336
_PNG_MAX_H = 336


def _parse_png_chunks(data: bytes) -> dict:
    chunks: dict = {}
    offset = 8
    while offset + 12 <= len(data):
        try:
            clen = struct.unpack(">I", data[offset:offset + 4])[0]
        except struct.error:
            break
        ctype = data[offset + 4:offset + 8]
        cdata = bytes(data[offset + 8:offset + 8 + clen])
        chunks.setdefault(ctype, []).append(cdata)
        if ctype == b"IEND":
            break
        offset += 12 + clen
    return chunks


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _decode_idat_rows(chunks: dict, width: int, height: int, color_type: int) -> list:
    """IDAT açar, PNG row filter'larını giderir. list[bytearray] döner."""
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise serializers.ValidationError(f"Desteklenmeyen renk tipi: {color_type}.")
    bpp = channels
    compressed = b"".join(chunks.get(b"IDAT", []))
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        raise serializers.ValidationError(f"PNG IDAT açılamadı: {exc}") from exc
    stride = 1 + width * bpp
    rows: list = []
    for y in range(height):
        s = y * stride
        ftype = raw[s]
        row = bytearray(raw[s + 1:s + 1 + width * bpp])
        prev = rows[y - 1] if y > 0 else bytearray(width * bpp)
        if ftype == 1:
            for x in range(bpp, len(row)):
                row[x] = (row[x] + row[x - bpp]) & 0xFF
        elif ftype == 2:
            for x in range(len(row)):
                row[x] = (row[x] + prev[x]) & 0xFF
        elif ftype == 3:
            for x in range(len(row)):
                a = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + (a + prev[x]) // 2) & 0xFF
        elif ftype == 4:
            for x in range(len(row)):
                a = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + _paeth(a, prev[x], prev[x - bpp] if x >= bpp else 0)) & 0xFF
        rows.append(row)
    return rows


def validate_barkod_logo_png(uploaded_file) -> None:
    """PNG doğrulama: max 336×336, ≤1 MB, şeffaf piksel yok.

    Dönüş öncesi dosya pozisyonu 0'a sıfırlanır.
    """
    if uploaded_file.size > _PNG_MAX_BYTES:
        raise serializers.ValidationError(
            f"Dosya boyutu 1 MB'ı aşamaz ({uploaded_file.size // 1024} KB yüklendi)."
        )
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    if len(data) < 33:
        raise serializers.ValidationError("Dosya çok küçük veya geçersiz.")
    if data[:8] != _PNG_MAGIC:
        raise serializers.ValidationError("Yalnızca PNG formatı kabul edilir.")
    if data[12:16] != b"IHDR":
        raise serializers.ValidationError("Geçersiz PNG: IHDR chunk bulunamadı.")
    width = struct.unpack(">I", data[16:20])[0]
    height = struct.unpack(">I", data[20:24])[0]
    bit_depth = data[24]
    color_type = data[25]
    if width > _PNG_MAX_W or height > _PNG_MAX_H:
        raise serializers.ValidationError(
            f"Görsel boyutu en fazla {_PNG_MAX_W}×{_PNG_MAX_H} px olabilir "
            f"({width}×{height} px yüklendi)."
        )
    if bit_depth != 8:
        raise serializers.ValidationError(f"Desteklenmeyen bit derinliği: {bit_depth} (yalnız 8-bit).")
    if color_type not in (0, 2, 3, 4, 6):
        raise serializers.ValidationError(f"Desteklenmeyen PNG renk tipi: {color_type}.")
    chunks = _parse_png_chunks(data)
    has_trns = b"tRNS" in chunks
    # Alfa kanalı olan tipler için şeffaflık kontrolü
    if color_type in (4, 6):
        try:
            rows = _decode_idat_rows(chunks, width, height, color_type)
        except serializers.ValidationError:
            raise
        except Exception as exc:
            raise serializers.ValidationError(f"PNG piksel verisi okunamadı: {exc}") from exc
        for row in rows:
            for x in range(width):
                alpha = row[x * 2 + 1] if color_type == 4 else row[x * 4 + 3]
                if alpha < 255:
                    raise serializers.ValidationError(
                        "Şeffaf piksel içeren görsel kabul edilmez. Arka plan beyaz olmalıdır."
                    )
    elif color_type == 3 and has_trns:
        trns = chunks[b"tRNS"][0]
        if any(v < 255 for v in trns):
            raise serializers.ValidationError(
                "Paletli PNG tRNS şeffaflığı kabul edilmez. Arka plan beyaz olmalıdır."
            )
    elif color_type == 0 and has_trns:
        raise serializers.ValidationError(
            "tRNS şeffaflığı kabul edilmez. Arka plan beyaz olmalıdır."
        )


# ─────────────────────────────────────────────────────────────────────────────
# CRUD Serializer
# ─────────────────────────────────────────────────────────────────────────────

class BarkodLogoSerializer(serializers.ModelSerializer):
    hedef_kiosk_idleri = serializers.PrimaryKeyRelatedField(
        source="hedef_kiosklar",
        many=True,
        read_only=True,
    )
    hedef_kiosk_idleri_write = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
        help_text="Hedef kiosk PK'larının listesi.",
    )

    class Meta:
        model = BarkodLogo
        fields = [
            "id",
            "ad",
            "media_url",
            "object_key",
            "checksum",
            "baslangic_zamani",
            "bitis_zamani",
            "aktif",
            "gunluk_baski_limiti",
            "hedef_kiosk_idleri",
            "hedef_kiosk_idleri_write",
            "olusturulma_tarihi",
        ]
        read_only_fields = ["id", "olusturulma_tarihi"]

    def validate(self, attrs):
        bas = attrs.get("baslangic_zamani") or (
            self.instance.baslangic_zamani if self.instance else None
        )
        bit = attrs.get("bitis_zamani") or (
            self.instance.bitis_zamani if self.instance else None
        )
        if bas and bit and bit <= bas:
            raise serializers.ValidationError(
                {"bitis_zamani": "Bitiş zamanı başlangıç zamanından sonra olmalıdır."}
            )
        return attrs

    def validate_gunluk_baski_limiti(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Günlük baskı limiti pozitif bir tam sayı olmalıdır.")
        return value

    def _sync_hedef_kiosklar(self, instance, kiosk_ids):
        from apps.pharmacies.models import Kiosk
        if kiosk_ids is not None:
            kiosklar = Kiosk.objects.filter(pk__in=kiosk_ids)
            instance.hedef_kiosklar.set(kiosklar)

    def create(self, validated_data):
        kiosk_ids = validated_data.pop("hedef_kiosk_idleri_write", [])
        instance = super().create(validated_data)
        self._sync_hedef_kiosklar(instance, kiosk_ids)
        return instance

    def update(self, instance, validated_data):
        kiosk_ids = validated_data.pop("hedef_kiosk_idleri_write", None)
        instance = super().update(instance, validated_data)
        self._sync_hedef_kiosklar(instance, kiosk_ids)
        return instance


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk Katalog Serializer (kiosk_api facade'da kullanılır)
# ─────────────────────────────────────────────────────────────────────────────

class BarkodLogoKatalogSerializer(serializers.ModelSerializer):
    """Kiosk katalog endpoint'inde kullanılan minimal payload."""

    media_url = serializers.SerializerMethodField()

    class Meta:
        model = BarkodLogo
        fields = [
            "id",
            "ad",
            "media_url",
            "object_key",
            "checksum",
            "baslangic_zamani",
            "bitis_zamani",
            "gunluk_baski_limiti",
        ]

    def get_media_url(self, obj):
        request = self.context.get("request")
        if obj.object_key:
            rel = f"/api/kiosk/v1/media/{obj.object_key}"
            if request is not None:
                return request.build_absolute_uri(rel)
            return rel
        return obj.media_url
