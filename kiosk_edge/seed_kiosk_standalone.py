"""
Standalone kiosk SQLite seed scripti.
Kullanım: python seed_kiosk_standalone.py [--db /path/to/local.db]

Config doğrulaması olmadan doğrudan SQLite'a seed yazar.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

# kiosk_edge/api dizinine erişim
_ROOT = pathlib.Path(__file__).resolve().parent
_SEED_PATH = _ROOT.parent / "master_seed.json"

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    icon: Mapped[str] = mapped_column(String(64), default="fa-circle")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="category")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    seed_id: Mapped[str] = mapped_column(String(32), unique=True)
    text: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    match_rules: Mapped[list] = mapped_column(JSON, default=list)

    category: Mapped["Category"] = relationship("Category", back_populates="questions")


async def seed(db_path: str, seed_path: pathlib.Path, force: bool) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        if not force:
            result = await session.execute(select(Category).limit(1))
            if result.scalar_one_or_none() is not None:
                print("Kiosk DB zaten dolu, seed atlandı. --force ile zorla.")
                await engine.dispose()
                return

        # Mevcut veriyi temizle (force modunda)
        if force:
            from sqlalchemy import text
            await session.execute(text("DELETE FROM questions"))
            await session.execute(text("DELETE FROM categories"))
            await session.commit()

        data = json.loads(seed_path.read_text(encoding="utf-8"))
        cats_created = 0
        qs_created = 0

        for cat_data in data:
            category = Category(
                slug=cat_data["category_slug"],
                name=cat_data["title"],
                icon=cat_data.get("icon", "fa-circle"),
                is_sensitive=False,
                is_active=True,
            )
            session.add(category)
            await session.flush()
            cats_created += 1

            for q_data in cat_data.get("questions", []):
                question = Question(
                    category_id=category.id,
                    seed_id=q_data["id"],
                    text=q_data["text"],
                    priority=q_data.get("priority", 0),
                    match_rules=q_data.get("match_rules", []),
                )
                session.add(question)
                qs_created += 1

        await session.commit()
        print(f"✓ Kiosk SQLite seed tamamlandı: {cats_created} kategori, {qs_created} soru → {db_path}")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kiosk SQLite seed")
    parser.add_argument("--db", default=str(_ROOT / "local_dev.db"), help="SQLite DB dosya yolu")
    parser.add_argument("--seed", default=str(_SEED_PATH), help="master_seed.json yolu")
    parser.add_argument("--force", action="store_true", help="Mevcut veriyi silip yeniden yükle")
    args = parser.parse_args()

    seed_path = pathlib.Path(args.seed)
    if not seed_path.exists():
        print(f"HATA: Seed dosyası bulunamadı: {seed_path}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(seed(args.db, seed_path, args.force))


if __name__ == "__main__":
    main()
