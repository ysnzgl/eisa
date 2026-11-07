"""
Admin API — /api/website/admin/ (CONTRACT §5).

Yetki: IsWebsiteEditor (superadmin veya editor). Yazmalar UnitOfWork üzerinden.
Liste uçları düz dizi döner; `medya` ve `basvurular` {count, results} ile sayfalanır.
"""
from __future__ import annotations

import os

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import ConcurrencyError, UnitOfWork
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from ..blocks import blok_tipleri_semasi, bloklari_dogrula
from ..models import (
    Basvuru,
    BlogKategori,
    BlogYazisi,
    MenuOgesi,
    Sayfa,
    SayfaRevizyon,
    SiteAyarlari,
    WebsiteMedya,
)
from ..permissions import IsWebsiteEditor
from ..serializers import (
    BasvuruSerializer,
    BlogKategoriSerializer,
    BlogYaziListeSerializer,
    BlogYaziSerializer,
    MedyaSerializer,
    SayfaMetaSerializer,
    SiteAyarlariSerializer,
)
from ..services import arama as arama_servisi
from ..services import medya as medya_servisi
from ..services.blog import okuma_suresi_hesapla
from ..services.menu import KONUMLAR, menu_agaci, menu_dogrula, menu_kaydet, menuler
from ..services.revalidate import blog_tagleri, revalidate, sayfa_tagleri
from ..services.sayfa import (
    KORUNAN_SLUGLAR,
    GeriAlmaHatasi,
    bloklari_kaydet,
    kullanici_adi,
    revizyon_geri_al,
    sayfa_detay,
    sayfa_ozet,
    sayfa_yayindan_kaldir,
    sayfa_yayinla,
    sayfa_yeniden_yukle,
    tarih,
)
from .preview import onizleme_url

CAKISMA_MESAJI = "Bu kayıt siz düzenlerken başka bir kullanıcı tarafından güncellendi. Sayfayı yenileyip tekrar deneyin."


class _AdminView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsWebsiteEditor]


class WebsiteSayfalama(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data, **ek):
        return Response({"count": self.page.paginator.count, "results": data, **ek})


def _cakisma(model, pk) -> Response:
    guncel = model.objects.filter(pk=pk).values_list("surum", flat=True).first()
    return Response({"detail": CAKISMA_MESAJI, "surum": guncel}, status=status.HTTP_409_CONFLICT)


def _surum_al(veri) -> tuple[int | None, Response | None]:
    ham = veri.get("surum") if isinstance(veri, dict) else None
    if ham is None:
        return None, Response({"surum": ["Bu alan zorunludur."]}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(ham, bool):
        ham = None
    try:
        return int(ham), None
    except (TypeError, ValueError):
        return None, Response({"surum": ["Geçerli bir tam sayı girin."]}, status=status.HTTP_400_BAD_REQUEST)


# ── Ayarlar ─────────────────────────────────────────────────────────────────


class AyarlarView(_AdminView):
    def get(self, request):
        return Response(SiteAyarlariSerializer(SiteAyarlari.getir()).data)

    def patch(self, request):
        ayarlar = SiteAyarlari.getir()
        ser = SiteAyarlariSerializer(ayarlar, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(ayarlar, k, v)
        with UnitOfWork(user=request.user) as uow:
            if ayarlar._state.adding:
                uow.add(ayarlar)
            else:
                uow.update(ayarlar)
            revalidate("site")
        return Response(SiteAyarlariSerializer(ayarlar).data)


# ── Blok tipleri ────────────────────────────────────────────────────────────


class BlokTipleriView(_AdminView):
    def get(self, request):
        return Response(blok_tipleri_semasi())


class AramaView(_AdminView):
    """GET ?q= — tüm site içeriğinde (taslak) arama; sonuç → ilgili editör + alan."""

    def get(self, request):
        return Response(arama_servisi.ara(request.query_params.get("q", "")))


# ── Menüler ─────────────────────────────────────────────────────────────────


class MenulerView(_AdminView):
    def get(self, request):
        return Response(menuler(public=False))


class MenuKonumView(_AdminView):
    def get(self, request, konum: str):
        if konum not in KONUMLAR:
            return Response({"detail": "Menü konumu bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        return Response(menu_agaci(konum, public=False))

    def put(self, request, konum: str):
        if konum not in KONUMLAR:
            return Response({"detail": "Menü konumu bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        temiz, hatalar = menu_dogrula(request.data)
        if hatalar:
            return Response(hatalar, status=status.HTTP_400_BAD_REQUEST)
        menu_kaydet(konum, temiz, user=request.user)
        return Response(menu_agaci(konum, public=False))


# ── Sayfalar ────────────────────────────────────────────────────────────────


def _sayfa_qs():
    return Sayfa.objects.select_related("aktif_revizyon").prefetch_related("bloklar")


class SayfalarView(_AdminView):
    def get(self, request):
        return Response([sayfa_ozet(s) for s in _sayfa_qs().order_by("sira", "id")])

    def post(self, request):
        ser = SayfaMetaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sayfa = Sayfa(**ser.validated_data)
        with UnitOfWork(user=request.user) as uow:
            uow.add(sayfa)
        return Response(sayfa_detay(sayfa_yeniden_yukle(sayfa.pk)), status=status.HTTP_201_CREATED)


class SayfaDetayView(_AdminView):
    def get(self, request, pk: int):
        sayfa = get_object_or_404(_sayfa_qs(), pk=pk)
        return Response(sayfa_detay(sayfa))

    def patch(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        surum, hata = _surum_al(request.data)
        if hata:
            return hata
        ser = SayfaMetaSerializer(sayfa, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        eski_slug = sayfa.slug
        for k, v in ser.validated_data.items():
            setattr(sayfa, k, v)
        try:
            with UnitOfWork(user=request.user) as uow:
                uow.update(sayfa, expected_version=surum)
                if sayfa.slug != eski_slug:
                    # Slug public adresi hemen değiştirir (snapshot slug taşımaz).
                    revalidate(*sayfa_tagleri(eski_slug), *sayfa_tagleri(sayfa.slug))
        except ConcurrencyError:
            return _cakisma(Sayfa, pk)
        return Response(sayfa_detay(sayfa_yeniden_yukle(pk)))

    def delete(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        if sayfa.slug in KORUNAN_SLUGLAR:
            return Response({"detail": "Bu sayfa silinemez."}, status=status.HTTP_400_BAD_REQUEST)
        kullanimlar = MenuOgesi.objects.filter(sayfa=sayfa).select_related("menu")
        if kullanimlar:
            yerler = ", ".join(f"{o.menu.get_konum_display()} › {o.etiket}" for o in kullanimlar)
            return Response(
                {"detail": f"Bu sayfa menüde kullanılıyor ({yerler}). Önce menüden kaldırın."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        yayindaydi = sayfa.durum == Sayfa.Durum.YAYINDA
        slug = sayfa.slug
        with UnitOfWork(user=request.user) as uow:
            uow.delete(sayfa)
            if yayindaydi:
                revalidate(*sayfa_tagleri(slug))
        return Response(status=status.HTTP_204_NO_CONTENT)


class SayfaBloklarView(_AdminView):
    def put(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        veri = request.data if isinstance(request.data, dict) else {}
        surum, hata = _surum_al(veri)
        if hata:
            return hata
        temiz, hatalar = bloklari_dogrula(veri.get("bloklar"))
        if hatalar:
            return Response({"bloklar": hatalar}, status=status.HTTP_400_BAD_REQUEST)
        try:
            bloklari_kaydet(sayfa, temiz, user=request.user, surum=surum)
        except ConcurrencyError:
            return _cakisma(Sayfa, pk)
        return Response(sayfa_detay(sayfa_yeniden_yukle(pk)))


class SayfaYayinlaView(_AdminView):
    def post(self, request, pk: int):
        sayfa = get_object_or_404(_sayfa_qs(), pk=pk)
        not_metni = request.data.get("not", "") if isinstance(request.data, dict) else ""
        try:
            sayfa_yayinla(sayfa, user=request.user, not_metni=str(not_metni or ""))
        except ConcurrencyError:
            return _cakisma(Sayfa, pk)
        return Response(sayfa_detay(sayfa_yeniden_yukle(pk)))


class SayfaYayindanKaldirView(_AdminView):
    def post(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        try:
            sayfa_yayindan_kaldir(sayfa, user=request.user)
        except ConcurrencyError:
            return _cakisma(Sayfa, pk)
        return Response(sayfa_detay(sayfa_yeniden_yukle(pk)))


class SayfaRevizyonlarView(_AdminView):
    def get(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        revizyonlar = SayfaRevizyon.objects.filter(sayfa=sayfa).select_related("yayinlayan").order_by("-yayin_tarihi", "-id")
        return Response(
            [
                {
                    "id": r.pk,
                    "yayinlayan_adi": kullanici_adi(r.yayinlayan),
                    "yayin_tarihi": tarih(r.yayin_tarihi),
                    "not": r.not_metni,
                    "aktif": r.pk == sayfa.aktif_revizyon_id,
                }
                for r in revizyonlar
            ]
        )


class RevizyonGeriAlView(_AdminView):
    def post(self, request, pk: int, rid: int):
        sayfa = get_object_or_404(_sayfa_qs(), pk=pk)
        rev = get_object_or_404(SayfaRevizyon, pk=rid, sayfa=sayfa)
        try:
            revizyon_geri_al(sayfa, rev, user=request.user)
        except GeriAlmaHatasi as exc:
            return Response(exc.hatalar, status=status.HTTP_400_BAD_REQUEST)
        except ConcurrencyError:
            return _cakisma(Sayfa, pk)
        return Response(sayfa_detay(sayfa_yeniden_yukle(pk)))


class SayfaOnizlemeView(_AdminView):
    def post(self, request, pk: int):
        sayfa = get_object_or_404(Sayfa, pk=pk)
        return Response({"url": onizleme_url("sayfa", sayfa.slug)})


# ── Blog kategorileri ───────────────────────────────────────────────────────


class BlogKategorilerView(_AdminView):
    def get(self, request):
        return Response(BlogKategoriSerializer(BlogKategori.objects.order_by("sira", "ad"), many=True).data)

    def post(self, request):
        ser = BlogKategoriSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        kategori = BlogKategori(**ser.validated_data)
        with UnitOfWork(user=request.user) as uow:
            uow.add(kategori)
            revalidate("blog")
        return Response(BlogKategoriSerializer(kategori).data, status=status.HTTP_201_CREATED)


class BlogKategoriDetayView(_AdminView):
    def get(self, request, pk: int):
        return Response(BlogKategoriSerializer(get_object_or_404(BlogKategori, pk=pk)).data)

    def patch(self, request, pk: int):
        kategori = get_object_or_404(BlogKategori, pk=pk)
        ser = BlogKategoriSerializer(kategori, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(kategori, k, v)
        with UnitOfWork(user=request.user) as uow:
            uow.update(kategori)
            revalidate(*blog_tagleri(*kategori.yazilar.values_list("slug", flat=True)))
        return Response(BlogKategoriSerializer(kategori).data)

    def delete(self, request, pk: int):
        kategori = get_object_or_404(BlogKategori, pk=pk)
        sluglar = list(kategori.yazilar.values_list("slug", flat=True))
        with UnitOfWork(user=request.user) as uow:
            uow.delete(kategori)
            revalidate(*blog_tagleri(*sluglar))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Blog yazıları ───────────────────────────────────────────────────────────


def _yazi_kaydet(yazi: BlogYazisi, validated: dict, *, user, surum: int | None) -> list[str]:
    """Alanları uygular, türetilen alanları hesaplar, kaydeder; revalidate edilecek slug'ları döner."""
    eski_slug = yazi.slug if yazi.pk else ""
    for k, v in validated.items():
        if k != "surum":
            setattr(yazi, k, v)
    yazi.okuma_suresi = okuma_suresi_hesapla(yazi.icerik_html)
    if yazi.durum == BlogYazisi.Durum.YAYINDA and yazi.yayin_tarihi is None:
        yazi.yayin_tarihi = timezone.now()
    with UnitOfWork(user=user) as uow:
        if yazi.pk is None:
            uow.add(yazi)
        else:
            uow.update(yazi, expected_version=surum)
        revalidate(*blog_tagleri(yazi.slug, eski_slug))
    return [yazi.slug, eski_slug]


class BlogYazilarView(_AdminView):
    def get(self, request):
        qs = BlogYazisi.objects.select_related("kategori").order_by("-guncellenme_tarihi", "-id")
        durum = request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return Response(BlogYaziListeSerializer(qs, many=True).data)

    def post(self, request):
        ser = BlogYaziSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        yazi = BlogYazisi()
        _yazi_kaydet(yazi, ser.validated_data, user=request.user, surum=None)
        return Response(BlogYaziSerializer(yazi).data, status=status.HTTP_201_CREATED)


class BlogYaziDetayView(_AdminView):
    def get(self, request, pk: int):
        return Response(BlogYaziSerializer(get_object_or_404(BlogYazisi, pk=pk)).data)

    def patch(self, request, pk: int):
        yazi = get_object_or_404(BlogYazisi, pk=pk)
        ser = BlogYaziSerializer(yazi, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            _yazi_kaydet(yazi, ser.validated_data, user=request.user, surum=ser.validated_data.get("surum"))
        except ConcurrencyError:
            return _cakisma(BlogYazisi, pk)
        return Response(BlogYaziSerializer(BlogYazisi.objects.get(pk=pk)).data)

    def delete(self, request, pk: int):
        yazi = get_object_or_404(BlogYazisi, pk=pk)
        slug = yazi.slug
        with UnitOfWork(user=request.user) as uow:
            uow.delete(yazi)
            revalidate(*blog_tagleri(slug))
        return Response(status=status.HTTP_204_NO_CONTENT)


class BlogYaziOnizlemeView(_AdminView):
    def post(self, request, pk: int):
        yazi = get_object_or_404(BlogYazisi, pk=pk)
        return Response({"url": onizleme_url("blog", yazi.slug)})


# ── Medya ───────────────────────────────────────────────────────────────────


class MedyaView(_AdminView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        qs = WebsiteMedya.objects.order_by("-olusturulma_tarihi", "-id")
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(dosya_adi__icontains=q) | Q(alt__icontains=q))
        sayfalama = WebsiteSayfalama()
        sayfa = sayfalama.paginate_queryset(qs, request, view=self)
        return sayfalama.get_paginated_response(MedyaSerializer(sayfa, many=True).data)

    def post(self, request):
        dosya = request.FILES.get("dosya")
        if dosya is None:
            return Response({"dosya": ["Bu alan zorunludur."]}, status=status.HTTP_400_BAD_REQUEST)
        alt = (request.data.get("alt") or "").strip()
        if len(alt) > 300:
            return Response({"alt": ["En fazla 300 karakter olabilir."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            mime, genislik, yukseklik = medya_servisi.dosyayi_incele(dosya)
        except medya_servisi.MedyaHatasi as exc:
            return Response({"dosya": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        object_key = medya_servisi.yeni_object_key(mime)
        medya_servisi.dosyayi_kaydet(dosya, object_key, mime)
        medya = WebsiteMedya(
            object_key=object_key,
            dosya_adi=os.path.basename(dosya.name or "")[:255],
            mime=mime,
            boyut=dosya.size,
            genislik=genislik,
            yukseklik=yukseklik,
            alt=alt,
        )
        try:
            with UnitOfWork(user=request.user) as uow:
                uow.add(medya)
        except Exception:
            medya_servisi.dosyayi_sil(object_key)
            raise
        return Response(MedyaSerializer(medya).data, status=status.HTTP_201_CREATED)


class MedyaDetayView(_AdminView):
    def get(self, request, pk: int):
        return Response(MedyaSerializer(get_object_or_404(WebsiteMedya, pk=pk)).data)

    def patch(self, request, pk: int):
        medya = get_object_or_404(WebsiteMedya, pk=pk)
        ser = MedyaSerializer(medya, data={"alt": request.data.get("alt", medya.alt)}, partial=True)
        ser.is_valid(raise_exception=True)
        medya.alt = (ser.validated_data.get("alt") or "").strip()
        with UnitOfWork(user=request.user) as uow:
            uow.update(medya)
        return Response(MedyaSerializer(medya).data)

    def delete(self, request, pk: int):
        medya = get_object_or_404(WebsiteMedya, pk=pk)
        object_key = medya.object_key
        with UnitOfWork(user=request.user) as uow:
            uow.delete(medya)
        medya_servisi.dosyayi_sil(object_key)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Başvurular ──────────────────────────────────────────────────────────────


def _yeni_sayisi() -> int:
    return Basvuru.objects.filter(durum=Basvuru.Durum.YENI).count()


class BasvurularView(_AdminView):
    def get(self, request):
        qs = Basvuru.objects.select_related("atanan").order_by("-olusturulma_tarihi", "-id")
        params = request.query_params
        if params.get("tip"):
            qs = qs.filter(tip=params["tip"])
        if params.get("durum"):
            qs = qs.filter(durum=params["durum"])
        q = (params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(ad_soyad__icontains=q) | Q(kurum__icontains=q) | Q(eposta__icontains=q)
                | Q(telefon__icontains=q) | Q(il__icontains=q)
            )
        sayfalama = WebsiteSayfalama()
        sayfa = sayfalama.paginate_queryset(qs, request, view=self)
        return sayfalama.get_paginated_response(
            BasvuruSerializer(sayfa, many=True).data, yeni_sayisi=_yeni_sayisi()
        )


class BasvuruOzetView(_AdminView):
    def get(self, request):
        return Response({"yeni": _yeni_sayisi()})


class BasvuruDetayView(_AdminView):
    def get(self, request, pk: int):
        return Response(BasvuruSerializer(get_object_or_404(Basvuru.objects.select_related("atanan"), pk=pk)).data)

    def patch(self, request, pk: int):
        basvuru = get_object_or_404(Basvuru, pk=pk)
        izinli = {k: v for k, v in request.data.items() if k in ("durum", "notlar", "atanan_id")}
        ser = BasvuruSerializer(basvuru, data=izinli, partial=True)
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(basvuru, k, v)
        with UnitOfWork(user=request.user) as uow:
            uow.update(basvuru)
        return Response(BasvuruSerializer(Basvuru.objects.select_related("atanan").get(pk=pk)).data)

    def delete(self, request, pk: int):
        basvuru = get_object_or_404(Basvuru, pk=pk)
        with UnitOfWork(user=request.user) as uow:
            uow.delete(basvuru)
        return Response(status=status.HTTP_204_NO_CONTENT)
