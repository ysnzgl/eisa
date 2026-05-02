"""SQLite bağlantı yönetimi (async SQLAlchemy)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(f"sqlite+aiosqlite:///{settings.sqlite_path}", future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Lokal SQLite şemasını oluşturur ve gerekirse seed'ler."""
    from . import models_local  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Tablolar boşsa master_seed.json'dan yükle
    from .seed_loader import seed_if_empty
    async with SessionLocal() as session:
        await seed_if_empty(session)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
