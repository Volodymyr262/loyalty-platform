"""
Unit tests for Celery tasks in the Loyalty application.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from core.context import reset_current_organization_id
from loyalty.models import Transaction
from loyalty.tasks import process_organization_expiration, process_yearly_points_expiration
from tests.factories.loyalty import CustomerFactory, TransactionFactory


class TestYearlyExpirationTask:
    """
    Tests for the logic inside the Celery Worker: process_organization_expiration.
    """

    def test_worker_logic_expires_points(self):
        """
        Scenario: The WORKER runs for a specific organization.
        """
        reset_current_organization_id()
        customer = CustomerFactory()
        org_id = customer.organization.id

        mock_today = datetime(2026, 1, 1, tzinfo=timezone.utc)
        earn_date = datetime(2024, 6, 15, tzinfo=timezone.utc)

        tx = TransactionFactory(
            customer=customer, amount=100, transaction_type=Transaction.EARN, organization=customer.organization
        )
        Transaction.objects.filter(id=tx.id).update(created_at=earn_date)

        # Act
        target_year = 2024

        with patch("loyalty.services.django_timezone.now", return_value=mock_today):
            result = process_organization_expiration(org_id, target_year)

        expiration_tx = Transaction.objects.filter(customer=customer, transaction_type=Transaction.EXPIRATION).first()

        assert expiration_tx is not None, f"Expiration transaction wasn't created! Task result: {result}"
        assert expiration_tx.amount == -100
        assert f"Org {org_id}: Expired 100 points" in result

    def test_worker_handles_exceptions(self):
        """
        Scenario: Worker encounters an error with one customer.
        Expected: Logs error, continues to next customer.
        """
        c1 = CustomerFactory()
        c2 = CustomerFactory(organization=c1.organization)
        org_id = c1.organization.id

        with patch("loyalty.tasks.LoyaltyService.process_yearly_expiration") as mock_service:

            def side_effect(cust, year):
                if cust.id == c1.id:
                    raise Exception("DB Boom")
                return 50

            mock_service.side_effect = side_effect

            result = process_organization_expiration(org_id, 2024)

            assert f"Org {org_id}: Expired 50 points for 1 customers" in result
            assert mock_service.call_count == 2

    @patch("loyalty.tasks.process_organization_expiration.delay")
    def test_dispatcher_logic(self, mock_delay):
        """
        Scenario: The DISPATCHER runs.
        Expected: It finds active organizations and calls .delay() for the worker.
        """
        c1 = CustomerFactory()  # Org 1 created
        c2 = CustomerFactory()  # Org 2 created (different org usually)

        result = process_yearly_points_expiration()

        # Assert
        assert "Dispatched" in result

        assert mock_delay.called
        assert mock_delay.call_count >= 2
