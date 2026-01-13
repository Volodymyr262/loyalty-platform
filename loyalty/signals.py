"""
Signals for the Loyalty application.
Handles cache invalidation when models are updated.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from loyalty.models import Campaign, Transaction


@receiver([post_save, post_delete], sender=Campaign)
def clear_campaign_cache(sender, instance, **kwargs):
    """
    Clears the active campaigns cache whenever a campaign is saved or deleted.
    This ensures that calculate_points() always uses up-to-date rules.
    """
    cache_key = f"active_campaigns:{instance.organization.id}"
    cache.delete(cache_key)


@receiver(post_save, sender=Transaction)
def invalidate_dashboard_cache(sender, instance, **kwargs):
    """
    Clears the dashboard cache for the specific organization
    whenever a transaction is created, updated, or deleted.
    """
    if instance.organization:
        cache_key = f"dashboard_stats:{instance.organization.id}"
        cache.delete(cache_key)
        # print(f" Cache cleared for organization: {instance.organization.name}")
