from django.contrib.auth import get_user_model


def test_superuser_role_is_forced_to_superadmin(db):
    user_model = get_user_model()

    user = user_model.objects.create_superuser(
        username="root_user",
        email="root@example.com",
        password="Str0ngPass!123",
        rol="pharmacist",
    )

    assert user.is_superuser is True
    assert user.rol == user_model.Rol.SUPERADMIN
