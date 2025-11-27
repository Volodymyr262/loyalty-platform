"""
Abstract base models providing multi-tenancy capabilities.
"""

from core.context import get_current_organization_id
from core.managers import TenantAwareManager
from django.db import models


class TenantAwareModel(models.Model):
    """
    Abstract base class for all models that must be isolated by tenant.

    It enforces two main behaviors:
    1. Data Isolation: Uses TenantAwareManager to restrict read access.
    2. Auto-Assignment: Automatically links new records to the active tenant on save.
    """

    # Link to the Organization (Tenant).
    # We use a string reference 'users.Organization' to avoid circular imports.
    # db_index=True is critical for performance as this column is used in almost every WHERE clause.
    organization = models.ForeignKey(
        "users.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_set",  # Generates dynamic names like 'transaction_set', 'campaign_set'
        db_index=True,
    )

    # Override the default manager to enforce isolation rules
    objects = TenantAwareManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Overridden save method to automatically assign the organization.
        """
        # If the organization is not explicitly set, try to get it from the context
        if not self.organization_id:
            org_id = get_current_organization_id()
            if org_id:
                self.organization_id = org_id

        super().save(*args, **kwargs)
