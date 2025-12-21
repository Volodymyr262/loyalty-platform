"""
Unit tests for the Loyalty Service logic.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from core.context import set_current_organization_id
from loyalty.models import Campaign, Transaction
from loyalty.services import LoyaltyService, calculate_points
from tests.factories.loyalty import CampaignFactory, CustomerFactory, TransactionFactory
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
        mock_now = datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc)

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
        # FIX: Removed 'datetime.' prefix
        mock_now = datetime(2025, 1, 1, 18, 0, 0, tzinfo=timezone.utc)

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


class TestLoyaltyExpiration:
    """
    Tests for the N+1 points expiration strategy.
    """

    def test_expiration_fifo_logic(self):
        """
        Scenario:
        - 2023: Earned 100 points.
        - 2024: Earned 50 points.
        - 2024: Spent 30 points (should come from 2023 balance).

        Action:
        - Run expiration for target year 2023.

        Expected:
        - 100 (Earned '23) - 30 (Spent Total) = 70 points should expire.
        - Balance should be 50 (only 2024 points remain).
        """
        customer = CustomerFactory()
        set_current_organization_id(customer.organization.id)
        service = LoyaltyService()

        # 1. Setup Data
        # Date in 2023.
        date_2023 = datetime(2023, 6, 1, tzinfo=timezone.utc)
        tx1 = TransactionFactory(customer=customer, amount=100, transaction_type=Transaction.EARN)
        # Manually update created_at because auto_now_add prevents setting it in factory
        Transaction.objects.filter(id=tx1.id).update(created_at=date_2023)

        # Date in 2024.
        date_2024 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        tx2 = TransactionFactory(customer=customer, amount=50, transaction_type=Transaction.EARN)
        Transaction.objects.filter(id=tx2.id).update(created_at=date_2024)

        # Spend 30 points (happened recently)
        service.process_transaction(customer, -30, "Coffee")

        # Current Balance: 100 + 50 - 30 = 120
        assert customer.get_balance() == 120

        # 2. Execute Expiration for 2023
        expired_amount = service.process_yearly_expiration(customer, target_year=2023)

        # 3. Assertions
        assert expired_amount == 70  # 100 old - 30 spent
        assert customer.get_balance() == 50  # Only 2024 points (50) should remain

        # Verify the transaction type
        expiration_tx = Transaction.objects.filter(customer=customer, transaction_type=Transaction.EXPIRATION).last()
        assert expiration_tx is not None
        assert expiration_tx.amount == -70

    def test_expiration_no_points_left(self):
        """
        Scenario: User spent everything they earned in the target year.
        Expected: 0 points expire.
        """
        customer = CustomerFactory()
        set_current_organization_id(customer.organization.id)
        service = LoyaltyService()

        # Earned 100 in 2023.
        date_2023 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        tx = TransactionFactory(customer=customer, amount=100)
        Transaction.objects.filter(id=tx.id).update(created_at=date_2023)

        # Spent 100 later
        service.process_transaction(customer, -100, "Big Purchase")

        # Run expiration
        expired = service.process_yearly_expiration(customer, target_year=2023)

        assert expired == 0
        assert customer.get_balance() == 0
