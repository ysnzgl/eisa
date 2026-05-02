"""
master_seed.json → SQLite seed yükleyici.
Uygulama başlangıcında tablolar boşsa verileri yazar.
"""
from __future__ import annotations

import json
import pathlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models_local import Category, Question

# master_seed.json, monorepo'nun bir üst dizinindedir:
# e-isa-monorepo/../master_seed.json
_SEED_PATH = pathlib.Path(__file__).parent.parent.parent / "master_seed.json"


async def seed_if_empty(session: AsyncSession) -> None:
    """Kategori tablosu boşsa master_seed.json'dan veri yükler."""
    result = await session.execute(select(Category).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Zaten veri var

    if not _SEED_PATH.exists():
        import logging
        logging.getLogger(__name__).warning("master_seed.json bulunamadı: %s", _SEED_PATH)
        return

    seed = json.loads(_SEED_PATH.read_text(encoding="utf-8"))

    for cat_data in seed:
        category = Category(
            slug=cat_data["category_slug"],
            name=cat_data["title"],
            icon=cat_data.get("icon", "fa-circle"),
            is_sensitive=False,
            is_active=True,
        )
        session.add(category)
        await session.flush()  # category.id oluşsun

        for q_data in cat_data.get("questions", []):
            question = Question(
                category_id=category.id,
                seed_id=q_data["id"],
                text=q_data["text"],
                priority=q_data.get("priority", 0),
                match_rules=q_data.get("match_rules", []),
            )
            session.add(question)

    await session.commit()
