"""
Models for the Loyalty application..
"""

from django.db import models

from core.models import TenantAwareModel


class Campaign(TenantAwareModel):
    """
    Represents a loyalty campaign defining how users earn points.
    e.g., "Welcome Bonus", "Purchase Reward".
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    points_value = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


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
