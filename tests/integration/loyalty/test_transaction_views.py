"""
Test for Transaction API endpoints.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Customer, Transaction
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import UserFactory


class TestTransactionAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization

        self.client.force_authenticate(user=self.user)
        set_current_organization_id(self.org.id)

        self.headers = {"HTTP_X_TENANT_API_KEY": self.org.api_key}

    def test_accrue_points_creates_transaction_and_customer(self):
        """
        POST /api/loyalty/transactions/
        Should create a transaction and a customer using 'external_id'.
        """
        payload = {
            "external_id": "USER_1001",
            "amount": 100.00,
            "description": "Coffee and Cake",
            "email": "new_client@example.com",
        }

        url = "/api/loyalty/transactions/"

        response = self.client.post(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED

        customer = Customer.objects.get(external_id="USER_1001", organization=self.org)
        assert customer.email == "new_client@example.com"

        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.customer == customer
        assert transaction.amount == 100.00

    def test_accrue_points_existing_customer(self):
        """
        POST /transactions/ with an existing external_id
        should link to the existing customer record.
        """
        existing_customer = Customer.objects.create(
            external_id="USER_EXISTING_99", organization=self.org, email="regular@example.com"
        )

        payload = {
            "external_id": "USER_EXISTING_99",  # Той самий ID
            "amount": 50.00,
            "description": "Morning Coffee",
        }

        response = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED

        assert Customer.objects.filter(organization=self.org).count() == 1

        transaction_id = response.data["id"]
        transaction = Transaction.objects.get(id=transaction_id)
        assert transaction.customer == existing_customer

    def test_create_transaction_validation_error(self):
        """
        POST /transactions/ without external_id should return 400 Bad Request.
        """
        payload = {"amount": 100.00}

        response = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "external_id" in response.data

    def test_list_transactions_isolation(self):
        """
        GET /transactions/ should only return transactions for the current tenant.
        """
        my_customer = Customer.objects.create(external_id="MY_CUST", organization=self.org)
        Transaction.objects.create(customer=my_customer, amount=100, transaction_type=Transaction.EARN)

        other_user = UserFactory()
        other_customer = Customer.objects.create(external_id="OTHER_CUST", organization=other_user.organization)

        set_current_organization_id(other_user.organization.id)

        Transaction.objects.create(customer=other_customer, amount=999, transaction_type=Transaction.EARN)

        set_current_organization_id(self.org.id)

        response = self.client.get("/api/loyalty/transactions/", **self.headers)

        assert response.status_code == status.HTTP_200_OK

        assert len(response.data) == 1
        assert response.data[0]["points"] == 100

    def test_accrue_points_applies_campaign_rules(self):
        """
        POST /transactions/
        Scenario: There is an active Campaign with x2 multiplier.
        Input Amount (Money): 100
        Expected Amount (Points): 200
        """
        # FIX: Explicitly set reward_type="multiplier" to avoid random "bonus" generation from Factory
        CampaignFactory(
            organization=self.org,
            name="Double Points",
            points_value=2,
            reward_type="multiplier",  # <-- Added this line
            is_active=True,
        )

        payload = {"external_id": "SHOP_USER_777", "amount": 100.00, "description": "Black Friday Purchase"}

        response = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED

        transaction = Transaction.objects.get(id=response.data["id"])

        assert transaction.amount == 200

    def test_campaign_rule_min_amount(self):
        """
        Scenario: Bonus +500 points ONLY if amount >= 1000.
        """
        # Create a campaign with a threshold rule
        CampaignFactory(
            organization=self.org,
            name="Big Spender",
            reward_type="bonus",  # Fixed bonus points
            points_value=500,  # +500 points
            rules={"min_amount": 1000},  # Logic: amount >= 1000
        )

        # Small purchase (100.00) -> Should get only base points (100)
        payload_small = {"external_id": "User_Small", "amount": 100.00}
        resp_small = self.client.post("/api/loyalty/transactions/", data=payload_small, **self.headers)

        assert resp_small.status_code == status.HTTP_201_CREATED
        assert resp_small.data["points"] == 100

        # Big purchase (1000.00) -> Should get Base (1000) + Bonus (500) = 1500
        payload_big = {"external_id": "User_Big", "amount": 1000.00}
        resp_big = self.client.post("/api/loyalty/transactions/", data=payload_big, **self.headers)

        assert resp_big.status_code == status.HTTP_201_CREATED
        assert resp_big.data["points"] == 1500

    def test_campaign_rule_welcome_bonus(self):
        """
        Scenario: +500 points for the VERY FIRST purchase only.
        """
        # Create a campaign for new users
        CampaignFactory(
            organization=self.org,
            name="Welcome Gift",
            reward_type="bonus",
            points_value=500,
            rules={"is_first_purchase": True},
        )

        payload = {"external_id": "Newbie_User", "amount": 100.00}

        # First purchase -> Should apply bonus
        # Calculation: 100 (base) + 500 (bonus) = 600
        resp_1 = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)
        assert resp_1.data["points"] == 600

        # Second purchase by the same user -> Should NOT apply bonus
        # Calculation: 100 (base) only
        resp_2 = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)
        assert resp_2.data["points"] == 100

    def test_campaign_rule_happy_hours(self):
        """
        Scenario: x2 Points between 14:00 and 16:00.
        """
        import datetime
        from unittest.mock import patch

        CampaignFactory(
            organization=self.org,
            name="Happy Hours",
            reward_type="multiplier",
            points_value=2,  # x2 multiplier
            rules={"start_time": "14:00", "end_time": "16:00"},
        )

        payload = {"external_id": "Coffee_Lover", "amount": 50.00}

        # Morning (10:00) -> Campaign should NOT apply
        mock_morning = datetime.datetime(2023, 1, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)

        # Mocking django.utils.timezone.now to return our fixed morning time
        with patch("django.utils.timezone.now", return_value=mock_morning):
            resp = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)
            assert resp.data["points"] == 50  # 50 * 1 (Base only)

        # Afternoon (15:00) -> Campaign SHOULD apply
        mock_happy_hour = datetime.datetime(2023, 1, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

        # Mocking time to simulate happy hour
        with patch("django.utils.timezone.now", return_value=mock_happy_hour):
            resp = self.client.post("/api/loyalty/transactions/", data=payload, **self.headers)
            assert resp.data["points"] == 100  # 50 * 2 (Multiplier applied)
