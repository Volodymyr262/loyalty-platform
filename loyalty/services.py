"""
Service layer for Loyalty business logic.
Handles point calculations, validations, and transaction processing.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from loyalty.models import Transaction


class LoyaltyService:
    """
    Encapsulates the rules for earning and spending points.
    """

    @transaction.atomic
    def process_transaction(self, customer, amount: int, description: str = "") -> Transaction:
        """
        Safely processes a point transaction.

        Args:
            customer: The Customer instance.
            amount: Integer (positive to earn, negative to spend).
            description: Reason for the transaction.

        Returns:
            The created Transaction object.

        Raises:
            ValidationError: If the customer tries to spend more points than they have.
        """

        # Validation Logic
        if amount < 0:
            # Check balance before spending
            current_balance = customer.get_balance()
            if current_balance + amount < 0:
                raise ValidationError(f"Insufficient funds. Balance: {current_balance}, Required: {abs(amount)}")

            tx_type = Transaction.SPEND
        else:
            tx_type = Transaction.EARN

        # Execution Logic
        # We rely on TenantAwareModel to automatically set the organization based on context
        # or we inherit it from the customer to be safe (customer.organization).
        # Since Transaction is TenantAwareModel, it usually needs the global context set,
        # but inheriting from customer is safer to avoid cross-tenant data leaks.

        new_transaction = Transaction.objects.create(
            customer=customer,
            amount=amount,
            transaction_type=tx_type,
            description=description,
            organization=customer.organization,
        )

        return new_transaction
