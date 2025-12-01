"""
Factories for the loyalty application
"""

import factory
from factory.django import DjangoModelFactory

from loyalty.models import Campaign, Customer
from tests.factories.users import OrganizationFactory


class CampaignFactory(DjangoModelFactory):
    """
    Factory for creating Campaign instances in tests.
    """

    class Meta:
        model = Campaign

    name = factory.Faker("catch_phrase")
    description = factory.Faker("sentence")
    points_value = factory.Faker("random_int", min=10, max=500)
    is_active = True

    organization = factory.SubFactory(OrganizationFactory)


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    # Generating unique id for every customer
    external_id = factory.Sequence(lambda n: f"client_{n}")

    organization = factory.SubFactory(OrganizationFactory)
