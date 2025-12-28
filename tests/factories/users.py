"""
Factories for the users application (tenants and users)
"""

import factory
from factory.django import DjangoModelFactory

from users.models import Organization, OrganizationApiKey, User


class OrganizationFactory(DjangoModelFactory):
    """
    Factory for creating Organization instances in tests.
    It ensures that each instance has a unique API key, required for tenant identity.
    """

    class Meta:
        model = Organization

    name = factory.Faker("company")
    is_active = True


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating User instances in tests.
    """

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    organization = factory.SubFactory(OrganizationFactory)


class OrganizationApiKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrganizationApiKey

    organization = factory.SubFactory(OrganizationFactory)
    name = "Default Test Key"
    key = factory.Faker("md5")  # Or specific logic to generate key
    is_active = True
