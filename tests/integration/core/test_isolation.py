"""
Integration tests for data isolation enforcement in the core module.
"""

import pytest
from core.context import reset_current_organization_id, set_current_organization_id
from core.models import TenantAwareManager, TenantAwareModel
from django.db import models

from tests.factories.users import OrganizationFactory


# Define a concrete model strictly for testing purposes
# This allows us to test the abstract TenantAwareModel logic in isolation
class SimpleDocument(TenantAwareModel):
    """
    A minimal model used to verify tenant isolation logic.
    """

    name = models.CharField(max_length=255)

    # We explicitly attach the manager to verify it filters data correctly
    objects = TenantAwareManager()

    class Meta:
        # app_label is required when defining models outside of standard apps
        app_label = "core"


@pytest.mark.django_db
def test_manager_enforces_tenant_isolation():
    """
    Verifies that TenantAwareManager automatically filters records
    based on the active organization context.
    """
    # Arrange: Create two distinct organizations using the imported Factory class
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()

    # Act: Create data for Organization A
    set_current_organization_id(org_a.id)
    doc_a = SimpleDocument.objects.create(name="Document A")

    # Act: Create data for Organization B
    set_current_organization_id(org_b.id)
    SimpleDocument.objects.create(name="Document B")

    # Assert: Switch context back to Organization A and query database
    reset_current_organization_id()
    set_current_organization_id(org_a.id)

    queryset_a = SimpleDocument.objects.all()

    # We expect to see ONLY Organization A's documents
    assert queryset_a.count() == 1
    assert queryset_a.first().id == doc_a.id

    # Cleanup context
    reset_current_organization_id()
