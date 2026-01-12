"""
Models for the Loyalty application..
"""

from django.core.cache import cache
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

    # multiplier when TYPE=MULTIPLIER or fixed amount when TYPE=BONUS
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
        cache_key = f"customer_balance:{self.id}"
        balance = cache.get(cache_key)

        if balance is not None:
            return balance

        balance = self.transactions.aggregate(total=Sum("amount"))["total"] or 0

        cache.set(cache_key, balance, timeout=60 * 60 * 24)

        return balance or 0


class Transaction(TenantAwareModel):
    """
    The Ledger (Journal).
    Records every point change (+ or -).
    The customer's balance is calculated as the sum of all their transactions.
    """

    EARN = "earn"
    SPEND = "spend"
    EXPIRATION = "expiration"

    TRANSACTION_TYPES = [(EARN, "Earn Points"), (SPEND, "Spend Points"), (EXPIRATION, "Points Expiration")]

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

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["transaction_type"]),
        ]

        # Order by newest first by default
        ordering = ["-created_at"]
