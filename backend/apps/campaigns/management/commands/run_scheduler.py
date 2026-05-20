"""``python manage.py run_scheduler``

APScheduler'ı PostgreSQL jobstore ile başlatır. docker-compose'daki
``scheduler`` servisi bu komutu çalıştırır.

Zamanlanmış işler:
  - nightly_generate  : Her gece 01:00 UTC → yarın için tüm kiosklara playlist
  - mark_kiosks_offline: Her 5 dakikada → ping gelmeyen kiosk'ları offline işaretle
"""
from __future__ import annotations

import logging
import signal
import sys

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "APScheduler'ı PostgreSQL jobstore ile başlatır (scheduler servisi)."

    def handle(self, *args, **options):
        # django-apscheduler import'ları
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        from django_apscheduler.jobstores import DjangoJobStore

        from apps.campaigns.jobs import mark_kiosks_offline, nightly_generate

        scheduler = BlockingScheduler(timezone="UTC")
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # ─── Job 1: Nightly playlist üretimi (her gece 01:00 UTC) ─────────
        scheduler.add_job(
            nightly_generate,
            trigger=CronTrigger(hour=1, minute=0),
            id="nightly_generate",
            name="Nightly Playlist Üretimi",
            jobstore="default",
            replace_existing=True,
            misfire_grace_time=3600,   # 1 saat geç başlasa da çalıştır
        )

        # ─── Job 2: Kiosk online/offline kontrolü (5 dakika) ──────────────
        scheduler.add_job(
            mark_kiosks_offline,
            trigger=IntervalTrigger(minutes=5),
            id="mark_kiosks_offline",
            name="Kiosk Offline İşaretleyici",
            jobstore="default",
            replace_existing=True,
            misfire_grace_time=60,
        )

        # Graceful shutdown
        def _shutdown(signum, frame):
            self.stdout.write("Scheduler durduruluyor…")
            scheduler.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)

        self.stdout.write(self.style.SUCCESS(
            "APScheduler (PostgreSQL jobstore) başlatıldı. "
            "Nightly: 01:00 UTC | Offline kontrol: 5dk"
        ))

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            connection.close()
