"""
Factories for the loyalty application
"""

import factory
from factory import fuzzy
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

    # Randomize points between 10 and 500
    points_value = factory.Faker("random_int", min=10, max=500)

    # Randomize the reward type to test both 'multiplier' and 'bonus' logic automatically
    reward_type = fuzzy.FuzzyChoice([x[0] for x in Campaign.REWARD_TYPES])

    # Default to empty dict to match model, but allow easy override.
    # We don't generate random JSON keys by default to avoid breaking
    # specific logic in the Rule Engine that expects valid keys (e.g. "min_amount").
    rules = factory.LazyFunction(dict)

    is_active = True
    organization = factory.SubFactory(OrganizationFactory)

    # TRAITS: This is a powerful FactoryBoy feature.
    # It allows to create specific "types" of campaigns easily in tests.
    # Usage: CampaignFactory(spending_rule=True)

    class Params:
        spending_rule = factory.Trait(
            rules={"min_amount": 1000, "multiplier": 2.0}, description="Campaign with minimum spend rule"
        )

        time_based = factory.Trait(
            rules={"start_time": "09:00", "end_time": "18:00"}, description="Happy hours campaign"
        )


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    # Generating unique id for every customer
    external_id = factory.Sequence(lambda n: f"client_{n}")

    organization = factory.SubFactory(OrganizationFactory)


class RewardFactory(DjangoModelFactory):
    """
    Factory for creating Reward instances.
    """

    class Meta:
        model = "loyalty.Reward"

    name = factory.Faker("catch_phrase")

    description = factory.Faker("sentence")
    point_cost = factory.Faker("random_int", min=50, max=1000)
    is_active = True

    organization = factory.SubFactory(OrganizationFactory)
