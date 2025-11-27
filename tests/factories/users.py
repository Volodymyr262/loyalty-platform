"""
Factories for the users application (tenants and users)
"""

import factory
from factory.django import DjangoModelFactory
from users.models import Organization


class OrganizationFactory(DjangoModelFactory):
    """
    Factory for creating Organization instances in tests.
    It ensures that each instance has a unique API key, required for tenant identity.
    """

    class Meta:
        model = Organization

    name = factory.Faker("company")
    # Generate a unique API key string using UUID format for realism
    api_key = factory.Faker("uuid4")
    is_active = True
