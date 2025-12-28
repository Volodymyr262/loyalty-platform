"""
Tests for Customer API endpoints.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from tests.factories.loyalty import CustomerFactory, TransactionFactory
from tests.factories.users import OrganizationApiKeyFactory, UserFactory


class TestCustomerAPI:
    """
    Integration tests for Customer viewing endpoints.
    Note: Customers are usually created automatically via Accruals,
    so this ViewSet is primarily Read-Only.
    """

    def setup_method(self):
        """
        Setup: Create User, Org, API Key and authenticate.
        """
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)

        # Generate API Key for Middleware authentication
        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

        set_current_organization_id(self.org.id)

    def test_list_customers_shows_balance(self):
        """
        GET /api/loyalty/customers/
        Should return a list of customers including their calculated balance field.
        """
        customer = CustomerFactory(organization=self.org, external_id="C1")
        TransactionFactory(customer=customer, amount=100)
        TransactionFactory(customer=customer, amount=50)

        url = "/api/loyalty/customers/"
        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["external_id"] == "C1"
        assert float(response.data[0]["balance"]) == 150.0

    def test_customer_isolation(self):
        """
        GET /api/loyalty/customers/
        Ensure we ONLY see customers belonging to our organization (Multi-tenancy).
        """
        CustomerFactory(organization=self.org, external_id="MY_CUST")

        # Other tenant's customer
        other_user = UserFactory()
        CustomerFactory(organization=other_user.organization, external_id="OTHER_CUST")

        url = "/api/loyalty/customers/"
        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["external_id"] == "MY_CUST"

    def test_search_customer_by_external_id(self):
        """
        GET /api/loyalty/customers/?search=...
        Verify that we can search customers by their external_id.
        """
        CustomerFactory(organization=self.org, external_id="Alice")
        CustomerFactory(organization=self.org, external_id="Bob")

        url = "/api/loyalty/customers/?search=Alice"
        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["external_id"] == "Alice"

    def test_create_customer_is_forbidden(self):
        """
        POST /api/loyalty/customers/
        Direct creation should be forbidden/not allowed.
        Customers are created implicitly via the Accrual endpoint.
        """
        url = "/api/loyalty/customers/"
        payload = {"external_id": "NEW"}
        response = self.client.post(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_customer_is_forbidden(self):
        """
        DELETE /api/loyalty/customers/{id}/
        Deletion is not allowed via API to preserve transaction history.
        """
        customer = CustomerFactory(organization=self.org)
        url = f"/api/loyalty/customers/{customer.id}/"
        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
