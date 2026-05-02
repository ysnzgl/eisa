"""
E-İSA Kiosk Lokal API.

Svelte UI yalnızca bu API ile (localhost:8765) konuşur. İnternet bağlantısının
durumundan bağımsız olarak Offline-First çalışır.

Endpoints:
  GET  /health                          — Sağlık kontrolü
  GET  /api/categories                  — Tüm aktif kategoriler (SQLite)
  GET  /api/categories/{slug}/questions — Kategoriye ait sorular + match_rules
  POST /api/session/submit              — Anket oturumunu outbox'a yaz
  GET  /api/session/{qr_code}           — QR koda göre oturum sorgula
  GET  /api/campaigns/active            — Aktif kampanyalar (Idle modu)
  POST /api/ad-impression               — Reklam gösterim logu
"""
from __future__ import annotations

import re
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_session, init_db
from .models_local import (
    AdImpressionOutbox,
    Campaign,
    Category,
    Question,
    SessionLogOutbox,
)
from .scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(
    title="E-ISA Kiosk Local API",
    version="0.1.0",
    description=(
        "E-İSA kiosk lokal API'si — Svelte UI ile localhost üzerinden haberleşir. "
        "İnternet bağlantısından bağımsız Offline-First çalışır.\n\n"
        "**Yetkilendirme**: `/api/session/{qr_code}` endpoint'i `Authorization: Bearer <LOCAL_SECRET>` başlığı gerektirir."
    ),
    openapi_tags=[
        {"name": "health", "description": "Servis sağlık kontrolü"},
        {"name": "categories", "description": "Aktif kategoriler ve sorular"},
        {"name": "session", "description": "Anket oturumu kayıt ve sorgulama"},
        {"name": "campaigns", "description": "Aktif kampanyalar (idle modu)"},
        {"name": "ad-impression", "description": "Reklam gösterim loglama"},
    ],
    docs_url="/docs" if settings.dev_mode else None,
    redoc_url="/redoc" if settings.dev_mode else None,
    openapi_url="/openapi.json" if settings.dev_mode else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic şemaları ──────────────────────────────────────────────────────

ALLOWED_AGE_RANGES = {"0-17", "18-25", "26-35", "36-50", "51-65", "65+"}
ALLOWED_GENDERS = {"M", "F", "male", "female", "other", "unspecified"}

_QR_RE = re.compile(r'^[A-Za-z0-9][\w:\-]{5,255}$')


class SessionSubmitRequest(BaseModel):
    age_range: str = Field(..., max_length=16)
    gender: str = Field(..., max_length=16)
    category_slug: str = Field(..., max_length=64)
    is_sensitive_flow: bool = False
    qr_code: str | None = Field(None, max_length=256)
    answers_payload: dict[str, Any] = {}
    suggested_ingredients: list[str] = []

    @field_validator("age_range")
    @classmethod
    def _check_age(cls, v: str) -> str:
        if v not in ALLOWED_AGE_RANGES:
            raise ValueError("Geçersiz yaş aralığı")
        return v

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str) -> str:
        if v not in ALLOWED_GENDERS:
            raise ValueError("Geçersiz cinsiyet değeri")
        return v

    @field_validator("qr_code")
    @classmethod
    def _check_qr(cls, v: str | None) -> str | None:
        if v is not None and not _QR_RE.match(v):
            raise ValueError("Geçersiz QR kodu formatı")
        return v

    @field_validator("suggested_ingredients")
    @classmethod
    def _limit_ingredients(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("Çok fazla bileşen")
        return v


class AdImpressionRequest(BaseModel):
    campaign_id: int = Field(..., ge=1)
    shown_at: str = Field(..., max_length=64)
    duration_ms: int = Field(0, ge=0, le=24 * 60 * 60 * 1000)


# ─── Lokal yetkilendirme ─────────────────────────────────────────────────────

def require_local_secret(authorization: str | None = Header(default=None)) -> None:
    expected = settings.local_api_secret
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Lokal API sırrı yapılandırılmamış.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Yetkilendirme başlığı eksik.")
    token = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Geçersiz lokal sır.")


# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/categories", tags=["categories"])
async def list_categories(db: AsyncSession = Depends(get_session)) -> list[dict]:
    """Aktif kategorileri döndürür."""
    result = await db.execute(
        select(Category).where(Category.is_active == True).order_by(Category.id)
    )
    categories = result.scalars().all()
    return [
        {
            "id": c.id,
            "slug": c.slug,
            "name": c.name,
            "icon": c.icon,
            "is_sensitive": c.is_sensitive,
        }
        for c in categories
    ]


@app.get("/api/categories/{slug}/questions", tags=["categories"])
async def list_questions(slug: str, db: AsyncSession = Depends(get_session)) -> list[dict]:
    """Kategorinin sorularını seed_id, match_rules ile döndürür."""
    cat_result = await db.execute(select(Category).where(Category.slug == slug))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")

    q_result = await db.execute(
        select(Question)
        .where(Question.category_id == category.id)
        .order_by(Question.priority)
    )
    questions = q_result.scalars().all()
    return [
        {
            "id": q.id,
            "seed_id": q.seed_id,
            "text": q.text,
            "priority": q.priority,
            "match_rules": q.match_rules,
        }
        for q in questions
    ]


@app.post("/api/session/submit", tags=["session"])
async def submit_session(
    body: SessionSubmitRequest,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Anket oturumunu SessionLogOutbox'a yazar."""
    qr = body.qr_code or uuid.uuid4().hex[:12].upper()

    payload = {
        "age_range": body.age_range,
        "gender": body.gender,
        "category_slug": body.category_slug,
        "is_sensitive_flow": body.is_sensitive_flow,
        "qr_code": qr,
        "answers_payload": body.answers_payload,
        "suggested_ingredients": body.suggested_ingredients,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    log_entry = SessionLogOutbox(payload=payload)
    db.add(log_entry)
    await db.commit()

    return {"qr_code": qr, "status": "saved"}


@app.get("/api/session/{qr_code:path}", tags=["session"])
async def get_session_by_qr(
    qr_code: str,
    db: AsyncSession = Depends(get_session),
    _auth: None = Depends(require_local_secret),
) -> dict:
    """QR koda göre oturum kaydını döndürür (lokal eczacı terminali)."""
    if not qr_code or len(qr_code) > 256 or not _QR_RE.match(qr_code):
        raise HTTPException(status_code=400, detail="Geçersiz QR kodu")

    from sqlalchemy import func, cast, String

    stmt = select(SessionLogOutbox).where(
        func.json_extract(cast(SessionLogOutbox.payload, String), "$.qr_code") == qr_code
    ).limit(1)
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=404, detail="QR koda ait oturum bulunamadı")

    return {"found": True, "session": log.payload}


@app.get("/api/campaigns/active", tags=["campaigns"])
async def active_campaigns(db: AsyncSession = Depends(get_session)) -> list[dict]:
    """Aktif kampanyaları döndürür."""
    now = datetime.now(timezone.utc)
    result = await db.execute(select(Campaign).where(Campaign.is_active == True))
    all_campaigns = result.scalars().all()

    active = []
    for c in all_campaigns:
        starts = c.starts_at.replace(tzinfo=timezone.utc) if c.starts_at.tzinfo is None else c.starts_at
        ends = c.ends_at.replace(tzinfo=timezone.utc) if c.ends_at.tzinfo is None else c.ends_at
        if starts <= now <= ends:
            active.append({
                "id": c.id,
                "name": c.name,
                "media_local_path": c.media_local_path,
                "targeting": c.targeting,
            })
    return active


@app.post("/api/ad-impression", status_code=201, tags=["ad-impression"])
async def log_ad_impression(
    body: AdImpressionRequest,
    db: AsyncSession = Depends(get_session),
) -> dict:
    impression = AdImpressionOutbox(payload={
        "campaign_id": body.campaign_id,
        "shown_at": body.shown_at,
        "duration_ms": body.duration_ms,
    })
    db.add(impression)
    await db.commit()
    return {"status": "logged"}
