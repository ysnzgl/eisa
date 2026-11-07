"""
Sayfa servisleri: taslak blok kaydı, yayınlama, yayından kaldırma, revizyon geri alma
ve sözleşmedeki (CONTRACT §3, §4, §5) JSON biçimlerinin üretimi.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.core.uow import UnitOfWork

from ..blocks import bloklari_dogrula
from ..models import Blok, Sayfa, SayfaRevizyon
from .medya import medya_referanslarini_tazele
from .revalidate import revalidate, sayfa_tagleri

KORUNAN_SLUGLAR = ("anasayfa", "kvkk", "cerez-politikasi")
AYRILMIS_SLUGLAR = ("blog", "api", "_next", "admin")

_tarih_alani = serializers.DateTimeField()


def tarih(dt):
    return _tarih_alani.to_representation(dt) if dt else None


def kullanici_adi(user) -> str:
    if user is None:
        return ""
    ad = f"{user.first_name} {user.last_name}".strip()
    return ad or user.username


# ── Snapshot ────────────────────────────────────────────────────────────────


def _taslak_bloklar(sayfa: Sayfa) -> list[Blok]:
    # prefetch_related("bloklar") ile gelmişse ek sorgu yapılmaz (Meta.ordering = sira, id).
    return sorted(sayfa.bloklar.all(), key=lambda b: (b.sira, b.pk))


def seo_snapshot_uret(sayfa: Sayfa) -> dict:
    return {
        "baslik": sayfa.baslik,
        "seo_baslik": sayfa.seo_baslik,
        "seo_aciklama": sayfa.seo_aciklama,
        "og_gorsel": sayfa.og_gorsel,
    }


def bloklar_snapshot_uret(sayfa: Sayfa) -> list[dict]:
    return [
        {
            "id": f"b_{b.pk}",
            "tip": b.tip,
            "anchor_id": b.anchor_id,
            "veri": b.veri,
            "gorunur": b.gorunur,
            "sira": i,
        }
        for i, b in enumerate(_taslak_bloklar(sayfa))
    ]


def _karsilastir(bloklar: list[dict]) -> list[tuple]:
    return [(b.get("tip"), b.get("anchor_id", ""), b.get("veri"), bool(b.get("gorunur", True))) for b in bloklar]


def taslak_degisti_mi(sayfa: Sayfa) -> bool:
    rev = sayfa.aktif_revizyon
    if rev is None:
        return True
    if seo_snapshot_uret(sayfa) != {k: rev.seo_snapshot.get(k) for k in ("baslik", "seo_baslik", "seo_aciklama", "og_gorsel")}:
        return True
    return _karsilastir(bloklar_snapshot_uret(sayfa)) != _karsilastir(rev.bloklar_snapshot or [])


# ── Admin JSON ──────────────────────────────────────────────────────────────


def sayfa_ozet(sayfa: Sayfa) -> dict:
    return {
        "id": sayfa.pk,
        "slug": sayfa.slug,
        "baslik": sayfa.baslik,
        "durum": sayfa.durum,
        "sira": sayfa.sira,
        "yayin_tarihi": tarih(sayfa.yayin_tarihi),
        "guncellenme_tarihi": tarih(sayfa.guncellenme_tarihi),
        "taslak_degisti": taslak_degisti_mi(sayfa),
        "surum": sayfa.surum,
    }


def sayfa_detay(sayfa: Sayfa) -> dict:
    d = sayfa_ozet(sayfa)
    d.update(
        {
            "seo_baslik": sayfa.seo_baslik,
            "seo_aciklama": sayfa.seo_aciklama,
            "og_gorsel": sayfa.og_gorsel,
            "bloklar": [
                {
                    "id": b.pk,
                    "tip": b.tip,
                    "veri": b.veri,
                    "sira": b.sira,
                    "gorunur": b.gorunur,
                    "anchor_id": b.anchor_id,
                }
                for b in _taslak_bloklar(sayfa)
            ],
        }
    )
    return d


def sayfa_yeniden_yukle(pk: int) -> Sayfa:
    return Sayfa.objects.select_related("aktif_revizyon").prefetch_related("bloklar").get(pk=pk)


# ── Public / Preview JSON ───────────────────────────────────────────────────


def _seo_cikti(seo: dict) -> dict:
    return {
        "baslik": seo.get("seo_baslik") or seo.get("baslik") or "",
        "aciklama": seo.get("seo_aciklama") or "",
        "og_gorsel": seo.get("og_gorsel"),
    }


def public_sayfa(sayfa: Sayfa) -> dict:
    """Aktif revizyon snapshot'ından (yalnızca gorunur=true bloklar)."""
    rev: SayfaRevizyon = sayfa.aktif_revizyon
    seo = rev.seo_snapshot or {}
    veri = {
        "slug": sayfa.slug,
        "baslik": seo.get("baslik") or sayfa.baslik,
        "seo": _seo_cikti(seo),
        "yayin_tarihi": tarih(rev.yayin_tarihi),
        "revizyon_id": rev.pk,
        "bloklar": [
            {"id": b["id"], "tip": b["tip"], "anchor_id": b.get("anchor_id", ""), "veri": b.get("veri") or {}}
            for b in (rev.bloklar_snapshot or [])
            if b.get("gorunur", True)
        ],
    }
    return medya_referanslarini_tazele(veri)


def onizleme_sayfa(sayfa: Sayfa) -> dict:
    """Taslak bloklardan public ile aynı biçim (CONTRACT §4)."""
    seo = seo_snapshot_uret(sayfa)
    veri = {
        "slug": sayfa.slug,
        "baslik": sayfa.baslik,
        "seo": _seo_cikti(seo),
        "yayin_tarihi": tarih(sayfa.yayin_tarihi),
        "revizyon_id": sayfa.aktif_revizyon_id,
        "bloklar": [
            {"id": f"b_{b.pk}", "tip": b.tip, "anchor_id": b.anchor_id, "veri": b.veri}
            for b in _taslak_bloklar(sayfa)
            if b.gorunur
        ],
    }
    return medya_referanslarini_tazele(veri)


# ── Yazma işlemleri ─────────────────────────────────────────────────────────


def bloklari_kaydet(sayfa: Sayfa, temiz_bloklar: list[dict], *, user, surum: int) -> None:
    """
    Taslak blokların TAMAMINI değiştirir. `id`'si gelen ve bu sayfaya ait bloklar güncellenir,
    gelmeyen eski bloklar silinir. Sayfa `surum` kontrolü (409) ilk adımda yapılır.
    """
    with UnitOfWork(user=user) as uow:
        uow.update(sayfa, expected_version=surum, update_fields=[])
        mevcut = {b.pk: b for b in Blok.objects.filter(sayfa=sayfa)}
        korunan: set[int] = set()
        for sira, girdi in enumerate(temiz_bloklar):
            blok = mevcut.get(girdi["id"]) if girdi["id"] not in korunan else None
            if blok is not None and blok.tip == girdi["tip"]:
                blok.veri = girdi["veri"]
                blok.sira = sira
                blok.gorunur = girdi["gorunur"]
                blok.anchor_id = girdi["anchor_id"]
                uow.update(blok)
                korunan.add(blok.pk)
            else:
                uow.add(
                    Blok(
                        sayfa=sayfa,
                        tip=girdi["tip"],
                        veri=girdi["veri"],
                        sira=sira,
                        gorunur=girdi["gorunur"],
                        anchor_id=girdi["anchor_id"],
                    )
                )
        silinecek = [pk for pk in mevcut if pk not in korunan]
        if silinecek:
            Blok.objects.filter(pk__in=silinecek).delete()


def sayfa_yayinla(sayfa: Sayfa, *, user, not_metni: str = "", revalidate_et: bool = True) -> SayfaRevizyon:
    simdi = timezone.now()
    with UnitOfWork(user=user) as uow:
        rev = SayfaRevizyon(
            sayfa=sayfa,
            bloklar_snapshot=bloklar_snapshot_uret(sayfa),
            seo_snapshot=seo_snapshot_uret(sayfa),
            yayinlayan=user if getattr(user, "pk", None) else None,
            yayin_tarihi=simdi,
            not_metni=(not_metni or "")[:500],
        )
        uow.add(rev)
        sayfa.aktif_revizyon = rev
        sayfa.durum = Sayfa.Durum.YAYINDA
        sayfa.yayin_tarihi = simdi
        uow.update(sayfa, update_fields=["aktif_revizyon_id", "durum", "yayin_tarihi"])
        if revalidate_et:
            revalidate(*sayfa_tagleri(sayfa.slug))
    return rev


def sayfa_yayindan_kaldir(sayfa: Sayfa, *, user) -> None:
    with UnitOfWork(user=user) as uow:
        sayfa.durum = Sayfa.Durum.TASLAK
        uow.update(sayfa, update_fields=["durum"])
        revalidate(*sayfa_tagleri(sayfa.slug))


class GeriAlmaHatasi(ValueError):
    def __init__(self, hatalar: dict):
        super().__init__("Revizyon güncel blok şemasına uymuyor.")
        self.hatalar = hatalar


def revizyon_geri_al(sayfa: Sayfa, rev: SayfaRevizyon, *, user) -> SayfaRevizyon:
    """Taslağı snapshot'tan yeniden kurar ve hemen yeni revizyon olarak yayınlar."""
    girdi = [
        {"tip": b.get("tip"), "veri": b.get("veri") or {}, "gorunur": b.get("gorunur", True), "anchor_id": b.get("anchor_id", "")}
        for b in (rev.bloklar_snapshot or [])
    ]
    temiz, hatalar = bloklari_dogrula(girdi)
    if hatalar:
        raise GeriAlmaHatasi({"bloklar": hatalar})

    seo = rev.seo_snapshot or {}
    with transaction.atomic():
        with UnitOfWork(user=user) as uow:
            Blok.objects.filter(sayfa=sayfa).delete()
            for sira, b in enumerate(temiz):
                uow.add(Blok(sayfa=sayfa, tip=b["tip"], veri=b["veri"], sira=sira, gorunur=b["gorunur"], anchor_id=b["anchor_id"]))
            sayfa.baslik = seo.get("baslik") or sayfa.baslik
            sayfa.seo_baslik = seo.get("seo_baslik") or ""
            sayfa.seo_aciklama = seo.get("seo_aciklama") or ""
            sayfa.og_gorsel = seo.get("og_gorsel")
            uow.update(sayfa, update_fields=["baslik", "seo_baslik", "seo_aciklama", "og_gorsel"])
        sayfa = sayfa_yeniden_yukle(sayfa.pk)
        return sayfa_yayinla(sayfa, user=user, not_metni=f"Revizyon #{rev.pk} geri alındı.")
