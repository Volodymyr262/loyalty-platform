import pytest
from rest_framework.test import APIClient


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
