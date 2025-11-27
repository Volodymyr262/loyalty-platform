"""
Custom Django managers for core functionality (multi-tenancy).
"""

from django.db import models

from core.context import get_current_organization_id


class TenantAwareManager(models.Manager):
    """
    A custom manager that automatically filters querysets based on the current
    active organization context.

    This ensures that a tenant can never access records belonging to another tenant,
    acting as the "Invisible Wall" at the ORM level.
    """

    def get_queryset(self):
        """
        Return a new QuerySet object filtered by the current organization.
        """
        # Get the standard queryset first (equivalent to objects.all())
        queryset = super().get_queryset()

        # Retrieve the currently active tenant ID from thread-local storage (contextvars)
        org_id = get_current_organization_id()

        # If a tenant context is active, force a filter on the queryset.
        # This applies to all subsequent chain calls (filter, exclude, get, etc.)
        if org_id:
            return queryset.filter(organization_id=org_id)

        # If no context is set (e.g., system tasks, management commands),
        # return the unfiltered queryset.
        return queryset
