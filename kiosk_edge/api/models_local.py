"""SQLite lokal modelleri — merkez şemasının kiosk projeksiyonu."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    icon: Mapped[str] = mapped_column(String(64), default="fa-circle")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="category", order_by="Question.priority")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    seed_id: Mapped[str] = mapped_column(String(32), unique=True)   # e.g. "en_q1"
    text: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    match_rules: Mapped[list] = mapped_column(JSON, default=list)  # [{gender, age_min, age_max, primary, supportive}]

    category: Mapped["Category"] = relationship("Category", back_populates="questions")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    media_local_path: Mapped[str] = mapped_column(String(512))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    targeting: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SessionLogOutbox(Base):
    """Henüz merkeze gönderilmemiş anket oturumu kayıtları."""

    __tablename__ = "session_log_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AdImpressionOutbox(Base):
    __tablename__ = "ad_impression_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
