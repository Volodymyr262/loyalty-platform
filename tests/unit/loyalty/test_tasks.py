"""
Unit tests for Celery tasks in the Loyalty application.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from core.context import set_current_organization_id
from loyalty.models import Transaction
from loyalty.tasks import process_yearly_points_expiration
from tests.factories.loyalty import CustomerFactory, TransactionFactory


class TestYearlyExpirationTask:
    """
    Tests for the logic inside the Celery task: process_yearly_points_expiration.
    These tests call the function synchronously (without the broker).
    """

    def test_task_execution_logic(self):
        """
        Scenario: The task runs successfully for a customer with old points.
        Expected: Points are expired, and the result string contains correct counts.
        """
        # 1. Setup Data
        customer = CustomerFactory()
        set_current_organization_id(customer.organization.id)

        # Simulate scenario:
        # Today is Jan 1st, 2026. Logic should target the year 2024.
        mock_today = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Earning date: Middle of 2024
        earn_date = datetime(2024, 6, 15, tzinfo=timezone.utc)

        tx = TransactionFactory(customer=customer, amount=100, transaction_type=Transaction.EARN)
        # Manually update created_at because auto_now_add prevents setting it in factory
        Transaction.objects.filter(id=tx.id).update(created_at=earn_date)

        # 2. Execute Task (Synchronously) with mocked time
        with patch("django.utils.timezone.now", return_value=mock_today):
            result = process_yearly_points_expiration()

        # 3. Assertions
        # Verify that an EXPIRATION transaction was created
        expiration_tx = Transaction.objects.filter(customer=customer, transaction_type=Transaction.EXPIRATION).first()

        assert expiration_tx is not None
        assert expiration_tx.amount == -100

        # Verify the output message from the task
        assert "Processed 1 customers" in result
        assert "Total expired: 100" in result

    def test_task_handles_exceptions_gracefully(self):
        """
        Scenario: One customer processing fails due to an error.
        Expected: The task should not crash; it should continue to the next customer.
        """
        # 1. Setup Data with Tenant Context
        # We must create customers in the SAME organization so we can test them in one batch.
        customer1 = CustomerFactory()
        CustomerFactory(organization=customer1.organization)

        set_current_organization_id(customer1.organization.id)

        # Mock the service to raise an error only for customer1
        with patch("loyalty.tasks.LoyaltyService.process_yearly_expiration") as mock_service:

            def side_effect(cust, year):
                if cust.id == customer1.id:
                    raise Exception("Database Error")
                return 50  # customer2 expires 50 points

            mock_service.side_effect = side_effect

            # Execute the task
            result = process_yearly_points_expiration()

            # Assertions
            # "Processed" count implies successful processing only (based on your task logic)
            # 1 failed, 1 succeeded -> "Processed 1"
            assert "Processed 1 customers" in result
            assert "Total expired: 50" in result

            # Verify that the service was attempted for both customers
            assert mock_service.call_count == 2
