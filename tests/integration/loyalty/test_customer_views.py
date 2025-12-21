from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Transaction
from tests.factories.loyalty import CustomerFactory
from tests.factories.users import UserFactory


class TestCustomerAPI:
    """
    Integration tests for /api/loyalty/customers/
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization

        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_TENANT_API_KEY": self.org.api_key}
        set_current_organization_id(self.org.id)

    def test_list_customers_shows_balance(self):
        """
        GET /customers/ should return customer list WITH calculated balance.
        """
        customer = CustomerFactory(organization=self.org, external_id="CUST_100")

        Transaction.objects.create(
            customer=customer, amount=200, transaction_type=Transaction.EARN, organization=self.org
        )

        response = self.client.get("/api/loyalty/customers/", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        customer_data = response.data[0]
        assert customer_data["external_id"] == "CUST_100"
        assert float(customer_data["balance"]) == 200.00

    def test_customer_isolation(self):
        """
        User should NOT see customers from other organizations.
        """
        CustomerFactory(organization=self.org, external_id="MY_CLIENT")

        other_user = UserFactory()
        CustomerFactory(organization=other_user.organization, external_id="ALIEN_CLIENT")

        response = self.client.get("/api/loyalty/customers/", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["external_id"] == "MY_CLIENT"

    def test_search_customer_by_external_id(self):
        """
        GET /customers/?search=XYZ should filter results.
        Useful for POS integration.
        """
        CustomerFactory(organization=self.org, external_id="ALICE")
        CustomerFactory(organization=self.org, external_id="BOB")

        # Search for BOB
        url = "/api/loyalty/customers/?search=BOB"
        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["external_id"] == "BOB"

    def test_create_customer_is_forbidden(self):
        """
        POST /customers/ should be 405 Method Not Allowed.
        Customers are created automatically via Accruals, not manually.
        """
        payload = {"external_id": "NEW_GUY"}
        response = self.client.post("/api/loyalty/customers/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_customer_is_forbidden(self):
        """
        DELETE /customers/{id}/ should be 405 Method Not Allowed.
        Deleting a customer would break transaction history integrity.
        """
        customer = CustomerFactory(organization=self.org)
        url = f"/api/loyalty/customers/{customer.id}/"

        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
