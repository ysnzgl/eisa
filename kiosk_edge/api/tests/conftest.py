"""
Kiosk Edge API test konfigurasyon ve fixture'ları.

Config modülü env değişkenlerini zorunlu kıldığı için,
import etmeden önce değerleri set ediyoruz.
"""
import os
import pytest
import pytest_asyncio

# Config modülü import edilmeden önce env değişkenlerini ayarla
os.environ.setdefault("EISA_KIOSK_APP_KEY", "test-app-key-for-testing-only")
os.environ.setdefault("EISA_KIOSK_MAC", "AA:BB:CC:DD:EE:FF")
os.environ.setdefault("EISA_CENTRAL_API_BASE", "http://127.0.0.1:9999")
os.environ.setdefault("EISA_LOCAL_API_SECRET", "test-local-secret")
os.environ.setdefault("EISA_SQLITE_PATH", ":memory:")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# kiosk_edge paketi olarak import et (PYTHONPATH = e-isa-monorepo/)
from kiosk_edge.api.database import Base, get_session
from kiosk_edge.api.main import app


TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    """Her test için taze in-memory SQLite."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session
