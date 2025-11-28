"""
Integration tests for data isolation enforcement in the core module.
"""

import pytest
from django.apps import apps
from django.db import connection, models

from core.context import reset_current_organization_id, set_current_organization_id
from core.models import TenantAwareManager, TenantAwareModel
from tests.factories.users import OrganizationFactory


@pytest.fixture
def concrete_tenant_model():
    """
    Creates a temporary concrete model based on the abstract TenantAwareModel.
    """

    # Define the model class dynamically
    class SimpleDocument(TenantAwareModel):
        name = models.CharField(max_length=255)
        objects = TenantAwareManager()

        class Meta:
            app_label = "core"

    # Manually create the table
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(SimpleDocument)

    yield SimpleDocument

    # Cleanup: Drop the table
    with connection.schema_editor() as schema_editor:
        schema_editor.delete_model(SimpleDocument)

    # This prevents "RuntimeWarning: Model was already registered" on the next test run
    try:
        del apps.all_models["core"]["simpledocument"]
        apps.clear_cache()
    except KeyError:
        pass


@pytest.mark.django_db(transaction=True)
def test_manager_enforces_tenant_isolation(concrete_tenant_model):
    """
    Verifies that TenantAwareManager automatically filters records
    based on the active organization context.
    """
    # Using the dynamic model from fixture
    SimpleDocument = concrete_tenant_model

    # Arrange: Create two distinct organizations
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


@pytest.mark.django_db(transaction=True)
def test_manager_returns_all_records_when_no_tenant_is_active(concrete_tenant_model):
    """
    Scenario: System access (e.g. Admin panel or Background task).
    Context: No organization is set.
    Expected: Manager should return ALL records from ALL tenants.
    """
    SimpleDocument = concrete_tenant_model

    # Arrange: Create data for different organizations
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()

    # Create documents
    set_current_organization_id(org_a.id)
    SimpleDocument.objects.create(name="Doc A")

    set_current_organization_id(org_b.id)
    SimpleDocument.objects.create(name="Doc B")

    # Act: Reset context (simulate Admin/System user)
    reset_current_organization_id()

    # Query without context
    queryset = SimpleDocument.objects.all()

    # Assert: We should see everything
    assert queryset.count() == 2
