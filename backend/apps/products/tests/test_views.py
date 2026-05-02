"""Products görünüm testleri — sync ve admin CRUD."""
import pytest
from apps.products.models import ActiveIngredient, Category, Question, Answer


@pytest.fixture
def category(db):
    return Category.objects.create(name="Enerji", slug="enerji", is_active=True)


@pytest.fixture
def inactive_category(db):
    return Category.objects.create(name="Pasif", slug="pasif", is_active=False)


@pytest.fixture
def ingredient(db):
    return ActiveIngredient.objects.create(name="Magnezyum", description="Temel mineral")


@pytest.mark.django_db
class TestProductSyncView:
    url = "/api/products/sync/"

    def test_unauthenticated_denied(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401

    def test_jwt_user_can_access(self, admin_client, category, ingredient):
        resp = admin_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data
        assert "ingredients" in data

    def test_kiosk_can_access(self, kiosk_client, category, ingredient):
        resp = kiosk_client.get(self.url)
        assert resp.status_code == 200

    def test_only_active_categories_returned(self, admin_client, category, inactive_category):
        resp = admin_client.get(self.url)
        slugs = [c["slug"] for c in resp.json()["categories"]]
        assert "enerji" in slugs
        assert "pasif" not in slugs

    def test_ingredients_ordered_by_name(self, admin_client):
        ActiveIngredient.objects.create(name="Çinko")
        ActiveIngredient.objects.create(name="A Vitamini")
        resp = admin_client.get(self.url)
        names = [i["name"] for i in resp.json()["ingredients"]]
        assert names == sorted(names)


@pytest.mark.django_db
class TestCategoryViewSet:
    list_url = "/api/products/categories/"

    def test_superadmin_can_create(self, admin_client):
        resp = admin_client.post(self.list_url, {
            "name": "Yeni Kategori", "slug": "yeni-kat"
        }, format="json")
        assert resp.status_code == 201

    def test_pharmacist_cannot_create(self, pharmacist_client):
        resp = pharmacist_client.post(self.list_url, {
            "name": "Hacker", "slug": "hacker"
        }, format="json")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self, api_client):
        resp = api_client.get(self.list_url)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestActiveIngredientViewSet:
    list_url = "/api/products/ingredients/"

    def test_superadmin_can_list(self, admin_client, ingredient):
        resp = admin_client.get(self.list_url)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Magnezyum" in names

    def test_superadmin_can_create(self, admin_client):
        resp = admin_client.post(self.list_url, {"name": "B12"}, format="json")
        assert resp.status_code == 201
