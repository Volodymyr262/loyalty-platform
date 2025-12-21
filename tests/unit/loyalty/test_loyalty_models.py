"""
Unit tests for Loyalty models (Campaign, Reward).
"""

import pytest
from django.core.exceptions import ValidationError

from core.context import set_current_organization_id
from core.models import TenantAwareModel
from loyalty.models import Campaign, Reward
from tests.factories.users import OrganizationFactory


class TestCampaignModel:
    """
    Tests for the Campaign model which defines how users earn points.
    """

    def test_campaign_inheritance(self):
        """
        Verify that Campaign inherits from TenantAwareModel to ensure data isolation.
        """
        assert issubclass(Campaign, TenantAwareModel)

    def test_create_campaign_defaults(self):
        """
        Verify that creating a campaign with minimal data sets correct defaults.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        campaign = Campaign.objects.create(name="Simple Campaign", points_value=10, is_active=True)

        assert campaign.reward_type == Campaign.TYPE_MULTIPLIER
        assert campaign.rules == {}

        assert "Multiplier" in str(campaign)

    def test_create_campaign_with_rules(self):
        """
        Verify that we can save JSON rules and specific reward types.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        campaign = Campaign.objects.create(
            name="Bonus for VIP",
            points_value=500,
            reward_type=Campaign.TYPE_BONUS,
            rules={"min_amount": 1000, "is_first_purchase": True},
            is_active=True,
        )

        assert campaign.reward_type == "bonus"
        assert campaign.rules["min_amount"] == 1000
        assert campaign.rules["is_first_purchase"] is True

        assert "Fixed Bonus" in str(campaign)

    def test_campaign_points_cannot_be_negative(self):
        """
        Verify that validation fails if points_value is negative.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        campaign = Campaign(name="Bad Campaign", points_value=-100, organization=org)

        with pytest.raises(ValidationError):
            campaign.full_clean()


class TestRewardModel:
    """
    Tests for the Reward model which defines what users can buy with points.
    """

    def test_reward_inheritance(self):
        """
        Verify that Reward inherits from TenantAwareModel.
        """
        assert issubclass(Reward, TenantAwareModel)

    def test_create_reward(self):
        """
        Verify that we can create a reward with a cost.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        reward = Reward.objects.create(
            name="Free Coffee",
            description="Get a free latte",
            point_cost=150,  # Ціна в балах
            is_active=True,
        )

        assert reward.id is not None
        assert reward.name == "Free Coffee"
        assert reward.point_cost == 150
        assert reward.organization == org
        assert str(reward) == "Free Coffee"
