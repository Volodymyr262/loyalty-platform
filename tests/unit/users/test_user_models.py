"""
Unit tests for the Organization model
"""

import pytest
from django.db.utils import IntegrityError

from tests.factories.users import OrganizationApiKeyFactory, OrganizationFactory, UserFactory


class TestOrganization:
    """
    Tests focused on the Organization model.
    """

    def test_organization_str_representation(self):
        """
        Tests the string representation of the Organization model.
        """
        org = OrganizationFactory(name="Super Duper Ltd")
        assert str(org) == "Super Duper Ltd"


class TestOrganizationApiKey:
    """
    Tests focused on the OrganizationApiKey model.
    """

    def test_organization_api_key_str_representation(self):
        """
        Tests the string representation of the OrganizationApiKey model.
        Expected format: '{Organization Name} - {Key Name}'
        """
        org = OrganizationFactory(name="Coffee Shop")
        api_key = OrganizationApiKeyFactory(organization=org, name="Website Widget")

        assert str(api_key) == "Coffee Shop - Website Widget"

    def test_api_key_uniqueness(self):
        """
        Tests that the 'key' field must be unique.
        """
        OrganizationApiKeyFactory(key="unique-key-123")

        with pytest.raises(IntegrityError):
            OrganizationApiKeyFactory(key="unique-key-123")


class TestUser:
    """
    Tests focused on the custom User model.
    """

    def test_user_str_representation(self):
        """
        Tests the string representation of the User model.
        Should return the email address.
        """
        user = UserFactory(email="admin@example.com")
        assert str(user) == "admin@example.com"
