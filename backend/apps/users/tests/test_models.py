"""User modeli testleri."""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_user_created_with_defaults(self):
        u = User.objects.create_user(username="eczaci1", password="pass")
        assert u.role == User.Role.PHARMACIST
        assert u.pharmacy is None

    def test_superadmin_role(self, superadmin):
        assert superadmin.role == "superadmin"

    def test_pharmacist_role(self, pharmacist):
        assert pharmacist.role == "pharmacist"

    def test_pharmacist_linked_to_pharmacy(self, pharmacist, pharmacy):
        assert pharmacist.pharmacy == pharmacy

    def test_db_table_name(self):
        assert User._meta.db_table == "users"

    def test_role_choices(self):
        choices = dict(User.Role.choices)
        assert "superadmin" in choices
        assert "pharmacist" in choices
