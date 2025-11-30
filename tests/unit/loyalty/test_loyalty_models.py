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

    def test_create_campaign(self):
        """
        Verify that we can create a campaign with valid data linked to a tenant.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        campaign = Campaign.objects.create(
            name="Welcome Bonus", description="Get points for registration", points_value=100, is_active=True
        )

        assert campaign.id is not None
        assert campaign.name == "Welcome Bonus"
        assert campaign.points_value == 100
        assert campaign.organization == org  # Auto-assigned by TenantAwareModel
        assert str(campaign) == "Welcome Bonus"

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
