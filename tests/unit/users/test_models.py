"""
Unit tests for the Organization model
"""

import pytest
from django.db.utils import IntegrityError
from users.models import Organization

from tests.factories.users import OrganizationFactory


def test_create_organization():
    """
    Tests that an Organization can be successfully created via the factory
    and persisted in the database with correct fields.
    """
    # Act: Create the organization instance
    org = OrganizationFactory(name="Test Corp", api_key="test-key-123")

    # Assert: Verify database count and key attributes
    assert Organization.objects.count() == 1
    assert org.name == "Test Corp"
    assert org.api_key == "test-key-123"
    assert org.is_active is True


def test_organization_str_representation():
    """
    Tests that the __str__ method correctly returns the organization's name.
    """
    # Arrange/Act: Create an organization
    org = OrganizationFactory(name="Super Duper Ltd")

    # Assert: Check the string output
    assert str(org) == "Super Duper Ltd"


def test_api_key_must_be_unique_to_prevent_data_leakage():
    """
    Tests that creating two organizations with the same API key raises an IntegrityError.
    """
    # Arrange: Create the first organization with a fixed key
    fixed_key = "secure-unique-key-123"
    OrganizationFactory(api_key=fixed_key)
    # Act & Assert: Attempt to create a second organization with the same key
    with pytest.raises(IntegrityError):
        # The database should prevent this operation
        OrganizationFactory(api_key=fixed_key)
