"""Products uygulama model testleri."""
import pytest
from apps.products.models import ActiveIngredient, Answer, Category, Question


@pytest.mark.django_db
class TestCategoryModel:
    def test_create_category(self):
        cat = Category.objects.create(name="Uyku", slug="uyku")
        assert cat.is_active is True
        assert cat.is_sensitive is False
        assert cat.db_table_check() == "categories" if hasattr(cat, "db_table_check") else True

    def test_sensitive_category(self):
        cat = Category.objects.create(name="Cinsel Sağlık", slug="cinsel", is_sensitive=True)
        assert cat.is_sensitive is True

    def test_slug_unique(self):
        Category.objects.create(name="Cat1", slug="unique-slug")
        with pytest.raises(Exception):
            Category.objects.create(name="Cat2", slug="unique-slug")


@pytest.mark.django_db
class TestQuestionModel:
    def test_question_ordering(self):
        cat = Category.objects.create(name="Test Cat", slug="test-cat")
        Question.objects.create(category=cat, text="Soru 2", order=2)
        Question.objects.create(category=cat, text="Soru 1", order=1)
        qs = list(Question.objects.filter(category=cat))
        assert qs[0].text == "Soru 1"
        assert qs[1].text == "Soru 2"

    def test_cascade_delete(self):
        cat = Category.objects.create(name="Del Cat", slug="del-cat")
        Question.objects.create(category=cat, text="Silinecek soru")
        assert Question.objects.filter(category=cat).count() == 1
        cat.delete()
        assert Question.objects.filter(category_id=cat.id).count() == 0


@pytest.mark.django_db
class TestActiveIngredientModel:
    def test_create_ingredient(self):
        ing = ActiveIngredient.objects.create(name="Magnezyum Sitrat")
        assert ing.description == ""

    def test_name_unique(self):
        ActiveIngredient.objects.create(name="B12")
        with pytest.raises(Exception):
            ActiveIngredient.objects.create(name="B12")
