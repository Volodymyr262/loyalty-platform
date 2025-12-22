"""
Signals for the Loyalty application.
Handles cache invalidation when models are updated.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from loyalty.models import Campaign


@receiver([post_save, post_delete], sender=Campaign)
def clear_campaign_cache(sender, instance, **kwargs):
    """
    Clears the active campaigns cache whenever a campaign is saved or deleted.
    This ensures that calculate_points() always uses up-to-date rules.
    """
    cache_key = f"active_campaigns:{instance.organization.id}"
    cache.delete(cache_key)