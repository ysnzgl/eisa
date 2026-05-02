"""Kiosk API endpoint testleri."""
import pytest
from datetime import datetime, timezone, timedelta

from kiosk_edge.api.models_local import Category, Campaign, SessionLogOutbox


pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCategoriesEndpoint:
    async def test_empty_categories(self, client):
        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_active_categories_returned(self, client, db):
        db.add(Category(slug="enerji", name="Enerji", is_active=True))
        db.add(Category(slug="pasif", name="Pasif", is_active=False))
        await db.commit()

        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        data = resp.json()
        slugs = [c["slug"] for c in data]
        assert "enerji" in slugs
        assert "pasif" not in slugs

    async def test_category_shape(self, client, db):
        db.add(Category(slug="uyku", name="Uyku", is_active=True, is_sensitive=False))
        await db.commit()

        resp = await client.get("/api/categories")
        cat = resp.json()[0]
        assert set(cat.keys()) == {"id", "slug", "name", "icon", "is_sensitive"}


class TestCategoryQuestionsEndpoint:
    async def test_unknown_category_404(self, client):
        resp = await client.get("/api/categories/yok/questions")
        assert resp.status_code == 404

    async def test_returns_questions(self, client, db):
        from kiosk_edge.api.models_local import Question
        cat = Category(slug="bagisiklik", name="Bağışıklık", is_active=True)
        db.add(cat)
        await db.flush()
        db.add(Question(category_id=cat.id, seed_id="q1", text="Soru 1", priority=0))
        await db.commit()

        resp = await client.get("/api/categories/bagisiklik/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["seed_id"] == "q1"
        assert "match_rules" in data[0]


class TestSessionSubmitEndpoint:
    async def test_submit_valid_session(self, client):
        payload = {
            "age_range": "26-35",
            "gender": "M",
            "category_slug": "enerji",
            "is_sensitive_flow": False,
            "answers_payload": {"q1": "evet"},
            "suggested_ingredients": ["Magnezyum"],
        }
        resp = await client.post("/api/session/submit", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "qr_code" in data
        assert data["status"] == "saved"

    async def test_auto_generated_qr_code(self, client):
        payload = {
            "age_range": "18-25",
            "gender": "F",
            "category_slug": "uyku",
        }
        resp = await client.post("/api/session/submit", json=payload)
        assert resp.status_code == 200
        qr = resp.json()["qr_code"]
        assert len(qr) > 0

    async def test_invalid_age_range_rejected(self, client):
        payload = {
            "age_range": "999-999",
            "gender": "M",
            "category_slug": "enerji",
        }
        resp = await client.post("/api/session/submit", json=payload)
        assert resp.status_code == 422

    async def test_invalid_gender_rejected(self, client):
        payload = {
            "age_range": "26-35",
            "gender": "X",
            "category_slug": "enerji",
        }
        resp = await client.post("/api/session/submit", json=payload)
        assert resp.status_code == 422

    async def test_too_many_ingredients_rejected(self, client):
        payload = {
            "age_range": "26-35",
            "gender": "M",
            "category_slug": "enerji",
            "suggested_ingredients": [f"ing{i}" for i in range(51)],
        }
        resp = await client.post("/api/session/submit", json=payload)
        assert resp.status_code == 422


class TestGetSessionEndpoint:
    SECRET = "test-local-secret"

    async def test_requires_auth(self, client, db):
        db.add(SessionLogOutbox(payload={"qr_code": "TESTABC123"}))
        await db.commit()
        resp = await client.get("/api/session/TESTABC123")
        assert resp.status_code == 401

    async def test_invalid_secret_denied(self, client, db):
        db.add(SessionLogOutbox(payload={"qr_code": "TESTABC123"}))
        await db.commit()
        resp = await client.get(
            "/api/session/TESTABC123",
            headers={"Authorization": "Bearer wrong-secret"}
        )
        assert resp.status_code == 401

    async def test_session_found(self, client, db):
        db.add(SessionLogOutbox(payload={"qr_code": "FOUND123", "age_range": "18-25"}))
        await db.commit()
        resp = await client.get(
            "/api/session/FOUND123",
            headers={"Authorization": f"Bearer {self.SECRET}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["session"]["qr_code"] == "FOUND123"

    async def test_session_not_found_404(self, client):
        resp = await client.get(
            "/api/session/NOTEXIST",
            headers={"Authorization": f"Bearer {self.SECRET}"}
        )
        assert resp.status_code == 404


class TestCampaignsEndpoint:
    async def test_empty_campaigns(self, client):
        resp = await client.get("/api/campaigns/active")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_active_campaign_within_range(self, client, db):
        now = datetime.now(timezone.utc)
        db.add(Campaign(
            name="Test Ad",
            media_local_path="/media/ad.mp4",
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
            is_active=True,
        ))
        await db.commit()

        resp = await client.get("/api/campaigns/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Ad"

    async def test_expired_campaign_not_returned(self, client, db):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        db.add(Campaign(
            name="Eski Reklam",
            media_local_path="/media/old.mp4",
            starts_at=past - timedelta(hours=1),
            ends_at=past,
            is_active=True,
        ))
        await db.commit()

        resp = await client.get("/api/campaigns/active")
        assert resp.json() == []


class TestAdImpressionEndpoint:
    async def test_log_impression(self, client):
        payload = {
            "campaign_id": 1,
            "shown_at": "2026-01-01T12:00:00Z",
            "duration_ms": 5000,
        }
        resp = await client.post("/api/ad-impression", json=payload)
        assert resp.status_code == 201
        assert resp.json() == {"status": "logged"}

    async def test_negative_campaign_id_rejected(self, client):
        resp = await client.post("/api/ad-impression", json={
            "campaign_id": -1,
            "shown_at": "2026-01-01T12:00:00Z",
            "duration_ms": 0,
        })
        assert resp.status_code == 422
