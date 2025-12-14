"""
Service layer for Loyalty business logic.
Handles point calculations, validations, and transaction processing.
"""

from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from loyalty.models import Campaign, Transaction


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
        # Or we inherit it from the customer to be safe (customer.organization).
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


def calculate_points(amount, customer):
    """
    Calculates points based on Amount + Active Campaigns (Rules & Types).
    """
    amount_decimal = Decimal(amount)
    base_points = int(amount_decimal)
    best_points = base_points

    organization = customer.organization

    now = timezone.localtime(timezone.now())
    current_time = now.time()

    campaigns = Campaign.objects.filter(organization=organization, is_active=True)

    for campaign in campaigns:
        rules = campaign.rules or {}
        is_applicable = True

        # RULE 1: Min Amount
        if "min_amount" in rules:
            min_amount = Decimal(str(rules["min_amount"]))
            if amount_decimal < min_amount:
                is_applicable = False

        # RULE 2: Welcome Bonus (First Purchase)
        if "is_first_purchase" in rules and rules["is_first_purchase"] is True:
            if customer.transactions.exists():
                is_applicable = False

        # RULE 3: Happy Hours (Time Window)
        if "start_time" in rules and "end_time" in rules:
            try:
                start = datetime.strptime(rules["start_time"], "%H:%M").time()
                end = datetime.strptime(rules["end_time"], "%H:%M").time()

                if not (start <= current_time <= end):
                    is_applicable = False
            except ValueError:
                pass

        if not is_applicable:
            continue

        # Calculation
        calculated_points = base_points

        if campaign.reward_type == Campaign.TYPE_MULTIPLIER:
            calculated_points = int(amount_decimal * Decimal(campaign.points_value))

        elif campaign.reward_type == Campaign.TYPE_BONUS:
            calculated_points = base_points + campaign.points_value

        if calculated_points > best_points:
            best_points = calculated_points

    return best_points
