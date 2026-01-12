import pytest
from rest_framework.test import APIClient

from core.context import reset_current_organization_id


@pytest.fixture
def api_client():
    """
    Fixture to provide an instance of DRF APIClient.
    """
    return APIClient()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enables database access for all tests.
    """
    pass


@pytest.fixture(autouse=True)
def cleanup_tenant_context():
    """
    Automatically resets the tenant context before and after EVERY test.
    This prevents context leakage between tests.
    """
    reset_current_organization_id()
    yield
    reset_current_organization_id()
