"""
Unit tests for the Loyalty Service logic.
"""

import datetime
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from core.context import set_current_organization_id
from loyalty.models import Campaign
from loyalty.services import LoyaltyService, calculate_points
from tests.factories.loyalty import CampaignFactory, CustomerFactory
from tests.factories.users import OrganizationFactory


class TestLoyaltyService:
    """
    Tests for business logic regarding points processing.
    """

    def test_earn_points_success(self):
        """
        Service should correctly create a transaction for earning points.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        customer = CustomerFactory(organization=org)

        service = LoyaltyService()
        transaction = service.process_transaction(customer=customer, amount=100, description="Bonus")

        assert transaction.amount == 100
        assert customer.get_balance() == 100

    def test_spend_points_success(self):
        """
        Service should allow spending if balance is sufficient.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        customer = CustomerFactory(organization=org)

        LoyaltyService().process_transaction(customer, 100, "Initial")

        transaction = LoyaltyService().process_transaction(customer=customer, amount=-30, description="Coffee")

        assert transaction.amount == -30
        assert customer.get_balance() == 70

    def test_spend_points_insufficient_funds(self):
        """
        Service should raise ValidationError if trying to spend more than balance.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)
        customer = CustomerFactory(organization=org)

        with pytest.raises(ValidationError) as exc:
            LoyaltyService().process_transaction(customer=customer, amount=-10, description="Fraud attempt")

        assert "Insufficient funds" in str(exc.value)

    def test_calculate_points_default_logic(self):
        """
        Scenario: No active campaigns exist.
        Expected: Points should be calculated with 1:1 ratio (default).
        """
        customer = CustomerFactory()
        set_current_organization_id(customer.organization.id)

        points = calculate_points(amount=100.0, customer=customer)
        assert points == 100

    def test_calculate_points_min_amount_ignored(self):
        """
        Scenario: Campaign exists but the transaction amount is too low to trigger it.
        Expected: Default 1:1 ratio should be applied, campaign rule ignored.
        """
        campaign = CampaignFactory(rules={"min_amount": 500}, points_value=2, reward_type=Campaign.TYPE_MULTIPLIER)
        set_current_organization_id(campaign.organization.id)
        customer = CustomerFactory(organization=campaign.organization)

        points = calculate_points(amount=100.0, customer=customer)

        assert points == 100

    def test_calculate_points_multiplier_applied(self):
        """
        Scenario: Campaign exists and rule is met.
        Expected: Multiplier should be applied.
        """
        campaign = CampaignFactory(rules={"min_amount": 50}, points_value=3, reward_type=Campaign.TYPE_MULTIPLIER)
        set_current_organization_id(campaign.organization.id)
        customer = CustomerFactory(organization=campaign.organization)

        points = calculate_points(amount=100.0, customer=customer)

        assert points == 300

    def test_calculate_points_welcome_bonus(self):
        """
        Scenario: 'is_first_purchase' rule.
        Expected: Bonus applied only if user has no previous transactions.
        """
        campaign = CampaignFactory(rules={"is_first_purchase": True}, points_value=50, reward_type=Campaign.TYPE_BONUS)
        set_current_organization_id(campaign.organization.id)
        customer = CustomerFactory(organization=campaign.organization)

        points = calculate_points(amount=100.0, customer=customer)
        assert points == 150

        from tests.factories.loyalty import TransactionFactory

        TransactionFactory(customer=customer)

        points_second = calculate_points(amount=100.0, customer=customer)
        assert points_second == 100

    def test_calculate_points_happy_hours_success(self):
        """
        Scenario: Transaction happens inside the defined time window.
        Expected: Multiplier applied.
        """
        mock_now = datetime.datetime(2025, 1, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)

        with patch("django.utils.timezone.now", return_value=mock_now):
            campaign = CampaignFactory(
                rules={"start_time": "13:00", "end_time": "15:00"}, points_value=2, reward_type=Campaign.TYPE_MULTIPLIER
            )
            set_current_organization_id(campaign.organization.id)
            customer = CustomerFactory(organization=campaign.organization)

            # Transaction at 14:00 falls between 13:00 and 15:00
            points = calculate_points(amount=100.0, customer=customer)

            # 100 * 2 = 200
            assert points == 200

    def test_calculate_points_happy_hours_outside_window(self):
        """
        Scenario: Transaction happens outside the time window.
        Expected: Default points (campaign ignored).
        """
        mock_now = datetime.datetime(2025, 1, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)

        with patch("django.utils.timezone.now", return_value=mock_now):
            campaign = CampaignFactory(
                rules={"start_time": "13:00", "end_time": "15:00"}, points_value=2, reward_type=Campaign.TYPE_MULTIPLIER
            )
            set_current_organization_id(campaign.organization.id)
            customer = CustomerFactory(organization=campaign.organization)

            # Transaction at 18:00 is outside 13:00-15:00 window
            points = calculate_points(amount=100.0, customer=customer)

            # Should be default 100
            assert points == 100
