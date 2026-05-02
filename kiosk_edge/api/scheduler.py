"""
APScheduler push/pull mantığı.

- PULL: Merkez API'den kategoriler, sorular ve hedefli reklamları çekip SQLite'a yazar.
- PUSH: Lokal outbox tablolarındaki anonim logları merkeze iter ve `pushed_at` işaretler.

Kiosk ↔ Merkez yetkilendirmesi: `Authorization: AppKey <key>` + `X-Kiosk-MAC: <mac>`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models_local import (
    AdImpressionOutbox,
    Campaign,
    Category,
    Question,
    SessionLogOutbox,
)

log = logging.getLogger("kiosk.scheduler")
_scheduler: AsyncIOScheduler | None = None


def _client() -> httpx.AsyncClient:
    """Merkez API için kimlik doğrulamalı HTTP istemcisi.

    UYARI: Bu istemcinin headers'ı log'a yazılmamalıdır — app_key içerir.
    """
    return httpx.AsyncClient(
        base_url=settings.central_api_base,
        headers={
            "Authorization": f"AppKey {settings.kiosk_app_key}",
            "X-Kiosk-MAC": settings.kiosk_mac,
        },
        timeout=15.0,
        verify=settings.verify_tls,
    )


async def pull_from_central() -> None:
    """
    Merkez Django API'den kategori/soru ve kampanya setlerini çeker,
    lokal SQLite'a upsert eder.
    """
    try:
        async with _client() as client:
            # ── 1. Ürün sync: kategoriler + sorular ─────────────────────
            resp = await client.get("/api/products/sync/")
            if resp.status_code == 200:
                data = resp.json()
                async with SessionLocal() as session:
                    # Kategorileri upsert et
                    for cat_data in data.get("categories", []):
                        existing = await session.get(Category, cat_data["id"])
                        if existing:
                            existing.name = cat_data["name"]
                            existing.slug = cat_data["slug"]
                            existing.is_sensitive = cat_data["is_sensitive"]
                            existing.is_active = cat_data.get("is_active", True)
                        else:
                            session.add(Category(
                                id=cat_data["id"],
                                slug=cat_data["slug"],
                                name=cat_data["name"],
                                is_sensitive=cat_data["is_sensitive"],
                                is_active=cat_data.get("is_active", True),
                            ))

                        # Kategoriye ait soruları upsert et
                        for q_data in cat_data.get("questions", []):
                            existing_q = await session.get(Question, q_data["id"])
                            if existing_q:
                                existing_q.text = q_data["text"]
                                existing_q.order = q_data.get("order", 0)
                            else:
                                session.add(Question(
                                    id=q_data["id"],
                                    category_id=cat_data["id"],
                                    text=q_data["text"],
                                    order=q_data.get("order", 0),
                                ))

                    await session.commit()
                log.info("PULL: %d kategori güncellendi", len(data.get("categories", [])))
            else:
                log.warning("PULL products/sync/ HTTP %s", resp.status_code)

            # ── 2. Kampanya sync ─────────────────────────────────────────
            resp = await client.get("/api/campaigns/sync/")
            if resp.status_code == 200:
                campaigns_data = resp.json()
                async with SessionLocal() as session:
                    for c in campaigns_data:
                        existing_c = await session.get(Campaign, c["id"])
                        # Tarih stringlerini datetime'a çevir
                        starts = datetime.fromisoformat(c["starts_at"].replace("Z", "+00:00"))
                        ends = datetime.fromisoformat(c["ends_at"].replace("Z", "+00:00"))
                        if existing_c:
                            existing_c.name = c["name"]
                            existing_c.media_local_path = c.get("media_url", "")
                            existing_c.starts_at = starts
                            existing_c.ends_at = ends
                            existing_c.targeting = {
                                "cities": c.get("target_cities", []),
                                "districts": c.get("target_districts", []),
                                "age_ranges": c.get("target_age_ranges", []),
                                "genders": c.get("target_genders", []),
                            }
                            existing_c.is_active = c.get("is_active", True)
                        else:
                            session.add(Campaign(
                                id=c["id"],
                                name=c["name"],
                                media_local_path=c.get("media_url", ""),
                                starts_at=starts,
                                ends_at=ends,
                                targeting={
                                    "cities": c.get("target_cities", []),
                                    "districts": c.get("target_districts", []),
                                    "age_ranges": c.get("target_age_ranges", []),
                                    "genders": c.get("target_genders", []),
                                },
                                is_active=c.get("is_active", True),
                            ))
                    await session.commit()
                log.info("PULL: %d kampanya güncellendi", len(campaigns_data))
            else:
                log.warning("PULL campaigns/sync/ HTTP %s", resp.status_code)

    except Exception:  # noqa: BLE001
        # Offline-First: hata yutulur, bir sonraki tetikte tekrar denenir
        log.exception("PULL başarısız (offline mod)")


async def push_to_central() -> None:
    """
    Outbox tablolarındaki (pushed_at=NULL) anonim logları merkeze iter,
    başarılı gönderilen kayıtlara pushed_at damgası vurur.
    """
    try:
        async with _client() as client:
            async with SessionLocal() as session:
                # ── 1. Oturum loglarını gönder ───────────────────────────
                result = await session.execute(
                    select(SessionLogOutbox)
                    .where(SessionLogOutbox.pushed_at.is_(None))
                    .limit(50)
                )
                session_items = result.scalars().all()

                if session_items:
                    resp = await client.post(
                        "/api/analytics/sessions/",
                        json={"items": [i.payload for i in session_items]},
                    )
                    if resp.status_code in (200, 201):
                        now = datetime.now(timezone.utc)
                        for item in session_items:
                            item.pushed_at = now
                        await session.commit()
                        log.info("PUSH: %d oturum logu gönderildi", len(session_items))
                    else:
                        log.warning("PUSH sessions HTTP %s", resp.status_code)

                # ── 2. Reklam impression loglarını gönder ────────────────
                imp_result = await session.execute(
                    select(AdImpressionOutbox)
                    .where(AdImpressionOutbox.pushed_at.is_(None))
                    .limit(100)
                )
                impression_items = imp_result.scalars().all()

                if impression_items:
                    resp = await client.post(
                        "/api/analytics/impressions/",
                        json={"items": [i.payload for i in impression_items]},
                    )
                    if resp.status_code in (200, 201):
                        now = datetime.now(timezone.utc)
                        for item in impression_items:
                            item.pushed_at = now
                        await session.commit()
                        log.info("PUSH: %d impression logu gönderildi", len(impression_items))
                    else:
                        log.warning("PUSH impressions HTTP %s", resp.status_code)

    except Exception:  # noqa: BLE001
        log.exception("PUSH başarısız (offline mod)")


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")
    _scheduler.add_job(pull_from_central, "interval", seconds=settings.pull_interval_sec)
    _scheduler.add_job(push_to_central, "interval", seconds=settings.push_interval_sec)
    _scheduler.start()
    log.info("Scheduler başlatıldı — pull:%ds push:%ds", settings.pull_interval_sec, settings.push_interval_sec)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
