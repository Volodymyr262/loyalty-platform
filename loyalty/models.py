"""
Models for the Loyalty application..
"""

from django.db import models
from django.db.models import Sum

from core.models import TenantAwareModel


class Campaign(TenantAwareModel):
    """
    Represents a loyalty campaign with flexible rules.
    """

    TYPE_MULTIPLIER = "multiplier"
    TYPE_BONUS = "bonus"

    REWARD_TYPES = [
        (TYPE_MULTIPLIER, "Multiplier (e.g. x2)"),
        (TYPE_BONUS, "Fixed Bonus (e.g. +100 points)"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_value = models.PositiveIntegerField()

    reward_type = models.CharField(max_length=20, choices=REWARD_TYPES, default=TYPE_MULTIPLIER)

    # JSON field for rules.
    # EXAMPLE: {"min_amount": 1000, "start_time": "14:00"}
    rules = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_reward_type_display()})"


class Reward(TenantAwareModel):
    """
    Represents an item or benefit that users can purchase using points.
    e.g., "Free Coffee", "10% Discount Coupon".
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    point_cost = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Customer(TenantAwareModel):
    """
    Represents a client of a specific Tenant.
    NOT a system user.
    """

    # External ID from the client's system
    external_id = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True, null=True)
    # Date when the customer joined the loyalty program
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure external_id is unique within a specific organization.
        # Two different tenants can have a customer with ID "123", but one tenant cannot have duplicates.
        unique_together = [("organization", "external_id")]

    def __str__(self):
        return f"{self.external_id} ({self.organization.name})"

    def get_balance(self):
        """
        Calculates the current balance by summing up all related transactions.
        Returns 0 if no transactions exist.
        """
        # 'transactions' is the related_name we defined in the Transaction model
        result = self.transactions.aggregate(total=Sum("amount"))["total"]

        # If there are no transactions, Sum returns None. We must return 0 instead.
        return result or 0


class Transaction(TenantAwareModel):
    """
    The Ledger (Journal).
    Records every point change (+ or -).
    The customer's balance is calculated as the sum of all their transactions.
    """

    EARN = "earn"
    SPEND = "spend"

    TRANSACTION_TYPES = [
        (EARN, "Earn Points"),
        (SPEND, "Spend Points"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="transactions",  # Allows accessing transactions via customer.transactions.all()
    )

    # Point amount.
    # Positive (+) = Earn
    # Negative (-) = Spend
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer} - {self.amount} ({self.get_transaction_type_display()})"
