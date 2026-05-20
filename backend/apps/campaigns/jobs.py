"""APScheduler job fonksiyonları — DOOH playlist otomatik üretimi.

Bu modül doğrudan import edilmez; ``run_scheduler`` management command'ı
APScheduler'a bu fonksiyonları kaydeder. PostgreSQL jobstore sayesinde
job state DB'de saklanır, scheduler yeniden başlayınca kayıplar olmaz.

Jobs:
  nightly_generate  — Her gece 01:00 UTC'de yarın için tüm kiosklara üretim.
  mark_offline      — Her 5 dakikada bir ping gelmeyen kiosk'ları offline işaretle.
"""
from __future__ import annotations

import datetime as _dt
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def nightly_generate() -> None:
    """Yarın için tüm aktif kioskların playlist'lerini üret.

    GenerationJob kaydı oluşturur, progress'i günceller; hata olsa da devam eder.
    """
    # Django ORM'yi lazy import: scheduler process'i başlarken app registry henüz
    # yüklenmemiş olabilir; fonksiyon çağrıldığında hazırdır.
    from apps.campaigns.models import GenerationJob
    from apps.campaigns.services.scheduler import generate_for_kiosk
    from apps.pharmacies.models import Kiosk

    tomorrow = (timezone.now() + _dt.timedelta(days=1)).date()
    kiosks = list(Kiosk.objects.filter(aktif=True))

    job = GenerationJob.objects.create(
        target_date=tomorrow,
        total_kiosks=len(kiosks),
        triggered_by="nightly",
        status=GenerationJob.JobStatus.RUNNING,
        started_at=timezone.now(),
    )
    logger.info("nightly_generate başladı: job=%s date=%s kiosk_count=%d",
                job.pk, tomorrow, len(kiosks))

    total_playlists = 0
    for kiosk in kiosks:
        try:
            playlists = generate_for_kiosk(kiosk, tomorrow)
            total_playlists += len(playlists)
            job.done_kiosks += 1
            logger.debug("  ✓ kiosk=%s -> %d playlist", kiosk.pk, len(playlists))
        except Exception:
            job.failed_kiosks += 1
            logger.exception("  ✗ kiosk=%s playlist üretimi başarısız", kiosk.pk)
        # Her kiosk sonrası progress'i kaydet
        GenerationJob.objects.filter(pk=job.pk).update(
            done_kiosks=job.done_kiosks,
            failed_kiosks=job.failed_kiosks,
            playlists_generated=total_playlists,
        )

    final_status = (
        GenerationJob.JobStatus.FAILED if job.done_kiosks == 0 and job.failed_kiosks > 0
        else GenerationJob.JobStatus.DONE
    )
    GenerationJob.objects.filter(pk=job.pk).update(
        status=final_status,
        playlists_generated=total_playlists,
        finished_at=timezone.now(),
    )
    logger.info("nightly_generate tamamlandı: job=%s status=%s playlists=%d",
                job.pk, final_status, total_playlists)


def regenerate_for_campaign(campaign_id: str) -> None:
    """Bir kampanyanın etkilediği kiosklarda bugün+yarın için playlist'i yeniden üret.

    Campaign kaydedildiğinde ``post_save`` sinyali bu fonksiyonu tetikler.
    """
    from apps.campaigns.models import Campaign, CampaignTarget, GenerationJob
    from apps.campaigns.services.scheduler import generate_for_kiosk
    from apps.pharmacies.models import Eczane, Kiosk

    try:
        campaign = Campaign.objects.prefetch_related("targets", "target_pharmacies").get(
            pk=campaign_id
        )
    except Campaign.DoesNotExist:
        logger.warning("regenerate_for_campaign: kampanya bulunamadı pk=%s", campaign_id)
        return

    # Etkilenen eczane id'lerini bul
    eczane_ids: set[int] = set()
    new_targets = list(campaign.targets.all())
    if new_targets:
        for t in new_targets:
            if t.target_type == CampaignTarget.TargetType.IL and t.il_id:
                eczane_ids.update(
                    Eczane.objects.filter(il_id=t.il_id).values_list("pk", flat=True)
                )
            elif t.target_type == CampaignTarget.TargetType.ILCE and t.ilce_id:
                eczane_ids.update(
                    Eczane.objects.filter(ilce_id=t.ilce_id).values_list("pk", flat=True)
                )
            elif t.target_type == CampaignTarget.TargetType.ECZANE and t.eczane_id:
                eczane_ids.add(t.eczane_id)
    else:
        legacy = campaign.target_pharmacies.all()
        if legacy.exists():
            eczane_ids.update(legacy.values_list("pk", flat=True))
        else:
            # Hedef yoksa tüm eczaneler
            eczane_ids.update(Eczane.objects.values_list("pk", flat=True))

    kiosks = list(Kiosk.objects.filter(aktif=True, eczane_id__in=eczane_ids))
    if not kiosks:
        return

    today = timezone.now().date()
    tomorrow = today + _dt.timedelta(days=1)
    dates = [today, tomorrow]

    job = GenerationJob.objects.create(
        target_date=today,
        total_kiosks=len(kiosks) * len(dates),
        triggered_by="campaign_change",
        status=GenerationJob.JobStatus.RUNNING,
        started_at=timezone.now(),
    )

    total = 0
    done = 0
    failed = 0
    for kiosk in kiosks:
        for d in dates:
            try:
                playlists = generate_for_kiosk(kiosk, d)
                total += len(playlists)
                done += 1
            except Exception:
                failed += 1
                logger.exception("regenerate_for_campaign: kiosk=%s date=%s", kiosk.pk, d)

    final_status = GenerationJob.JobStatus.DONE if done > 0 else GenerationJob.JobStatus.FAILED
    GenerationJob.objects.filter(pk=job.pk).update(
        status=final_status,
        done_kiosks=done,
        failed_kiosks=failed,
        playlists_generated=total,
        finished_at=timezone.now(),
    )
    logger.info("regenerate_for_campaign: campaign=%s playlists=%d status=%s",
                campaign_id, total, final_status)


def mark_kiosks_offline() -> None:
    """5 dakikadan fazla ping göndermeyen kioskları offline işaretle."""
    from apps.pharmacies.models import Kiosk

    threshold = timezone.now() - _dt.timedelta(minutes=5)
    updated = Kiosk.objects.filter(
        aktif=True, son_goruldu__lt=threshold, is_online=True
    ).update(is_online=False)
    if updated:
        logger.info("mark_kiosks_offline: %d kiosk offline işaretlendi", updated)
