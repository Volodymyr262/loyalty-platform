"""
Test for Transaction API endpoints.
Updated to support CQRS (Separated Accruals and History).
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Customer, Transaction
from tests.factories.loyalty import CampaignFactory, CustomerFactory, TransactionFactory
from tests.factories.users import OrganizationApiKeyFactory, UserFactory


class TestAccrualAPI:
    """
    Tests specifically for POST /api/loyalty/accruals/ (Earning points).
    """

    def setup_method(self):
        """
        Setup: Create User, Org, generate API Key for Middleware authentication.
        """
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization

        self.client.force_authenticate(user=self.user)
        set_current_organization_id(self.org.id)

        # Create API Key via the new model and set headers
        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

    def test_accrue_points_creates_transaction_and_customer(self):
        """
        POST /api/loyalty/accruals/
        Should create a transaction and automatically create a new customer
        if 'external_id' does not exist yet.
        """
        payload = {
            "external_id": "USER_1001",
            "amount": 100.00,
            "description": "Coffee and Cake",
            "email": "new_client@example.com",
        }

        url = "/api/loyalty/accruals/"
        response = self.client.post(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED

        customer = Customer.objects.get(external_id="USER_1001", organization=self.org)
        assert customer.email == "new_client@example.com"

        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.customer == customer
        assert transaction.amount == 100.00

    def test_accrue_points_existing_customer(self):
        """
        POST /api/loyalty/accruals/
        Should successfully accrue points to an existing customer.
        """
        existing_customer = CustomerFactory(
            external_id="USER_EXISTING_99", organization=self.org, email="regular@example.com"
        )

        payload = {
            "external_id": "USER_EXISTING_99",
            "amount": 50.00,
            "description": "Morning Coffee",
        }

        response = self.client.post("/api/loyalty/accruals/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.customer == existing_customer

    def test_create_transaction_validation_error(self):
        """
        POST /api/loyalty/accruals/
        Missing required fields (like external_id) should return 400 Bad Request.
        """
        payload = {"amount": 100.00}
        response = self.client.post("/api/loyalty/accruals/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "external_id" in response.data

    def test_accrue_points_applies_campaign_rules(self):
        """
        POST /api/loyalty/accruals/
        Should apply active campaign multipliers (e.g., x2 points).
        """
        CampaignFactory(
            organization=self.org,
            name="Double Points",
            points_value=2,
            reward_type="multiplier",
            is_active=True,
        )

        payload = {"external_id": "SHOP_USER_777", "amount": 100.00, "description": "Black Friday"}
        response = self.client.post("/api/loyalty/accruals/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.amount == 200

    def test_campaign_rule_min_amount(self):
        """
        POST /api/loyalty/accruals/
        Should verify that campaign rules (e.g., min_amount) are respected.
        """
        CampaignFactory(
            organization=self.org,
            reward_type="bonus",
            points_value=500,
            rules={"min_amount": 1000},
        )

        # 1. Small purchase (No bonus)
        payload_small = {"external_id": "User_Small", "amount": 100.00}
        resp_small = self.client.post("/api/loyalty/accruals/", data=payload_small, **self.headers)
        assert resp_small.status_code == status.HTTP_201_CREATED
        assert resp_small.data["points"] == 100

        # 2. Big purchase (Applies bonus)
        payload_big = {"external_id": "User_Big", "amount": 1000.00}
        resp_big = self.client.post("/api/loyalty/accruals/", data=payload_big, **self.headers)
        assert resp_big.status_code == status.HTTP_201_CREATED
        assert resp_big.data["points"] == 1500

    def test_accrual_negative_amount_blocked_by_serializer(self):
        """
        POST /api/loyalty/accruals/
        Negative amounts should be blocked by validation (must use Redemption endpoint for spending).
        """
        payload = {"external_id": "POOR_GUY", "amount": -100.00, "description": "Hacking attempt"}
        response = self.client.post("/api/loyalty/accruals/", data=payload, **self.headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be positive" in str(response.data)


class TestTransactionHistoryAPI:
    """
    Tests specifically for GET /api/loyalty/transactions/ (Read Only History).
    """

    def setup_method(self):
        """
        Setup: Create User, Org, generate API Key for Middleware authentication.
        """
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)

        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

        set_current_organization_id(self.org.id)

    def test_list_transactions_isolation(self):
        """
        GET /api/loyalty/transactions/
        Ensure we ONLY see transactions belonging to our organization (Multi-tenancy isolation).
        """
        TransactionFactory(
            customer__organization=self.org,
            customer__external_id="MY_CUST",
            amount=100,
            transaction_type=Transaction.EARN,
        )

        # Create data for ANOTHER tenant
        other_user = UserFactory()
        TransactionFactory(customer__organization=other_user.organization, amount=999)

        set_current_organization_id(self.org.id)

        response = self.client.get("/api/loyalty/transactions/", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["points"] == 100
