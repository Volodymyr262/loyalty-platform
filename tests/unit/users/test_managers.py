"""
Unit tests for CustomUserManager to cover edge cases.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


class TestCustomUserManager:
    """
    Test suite for User Manager logic (create_user, create_superuser).
    """

    def test_create_user_without_email_raises_error(self):
        """
        Ensure create_user raises ValueError if email is missing.
        """
        with pytest.raises(ValueError) as exc:
            User.objects.create_user(email=None, password="password123")

        assert "The Email must be set" in str(exc.value)

    def test_create_superuser_success(self):
        """
        Ensure create_superuser sets is_staff and is_superuser to True.
        """
        admin_user = User.objects.create_superuser(email="admin@test.com", password="password123")

        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
        assert admin_user.is_active is True

    def test_create_superuser_fails_without_staff_flag(self):
        """
        Ensure create_superuser raises error if is_staff is set to False.
        """
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="admin2@test.com", password="password123", is_staff=False)

    def test_create_superuser_fails_without_superuser_flag(self):
        """
        Ensure create_superuser raises error if is_superuser is set to False.
        """
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="admin3@test.com", password="password123", is_superuser=False)
