"""
Unit tests for the Loyalty Service logic.
"""

import pytest
from django.core.exceptions import ValidationError

from core.context import set_current_organization_id
from loyalty.services import LoyaltyService
from tests.factories.loyalty import CustomerFactory
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
