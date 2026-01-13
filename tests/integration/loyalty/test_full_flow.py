"""
Integration tests for the full Loyalty lifecycle using Factories.
Includes checks for:
1. Multi-tenancy isolation.
2. End-to-end Accrual -> Redemption flow.
3. Complex Expiration logic (verifying the fix).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework import status

from loyalty.models import Customer, Transaction
from loyalty.services import LoyaltyService
from tests.factories.loyalty import CustomerFactory, TransactionFactory
from tests.factories.users import OrganizationApiKeyFactory, OrganizationFactory


@pytest.fixture
def tenant_a():
    return OrganizationFactory(name="Tenant A")


@pytest.fixture
def tenant_b():
    return OrganizationFactory(name="Tenant B")


@pytest.fixture
def api_key_a(tenant_a):
    """Creates an API key for Tenant A and returns the raw key string."""
    key_value = "tenant-a-secret-key"
    OrganizationApiKeyFactory(organization=tenant_a, key=key_value)
    return key_value


@pytest.fixture
def api_key_b(tenant_b):
    """Creates an API key for Tenant B and returns the raw key string."""
    key_value = "tenant-b-secret-key"
    OrganizationApiKeyFactory(organization=tenant_b, key=key_value)
    return key_value


@pytest.mark.django_db
class TestLoyaltySystemIntegration:
    def test_tenant_isolation_in_api(self, api_client, tenant_a, api_key_a, tenant_b, api_key_b):
        """
        Scenario:
        1. Tenant A has a customer.
        2. Tenant B requests customer list.
        3. Tenant B should see 0 customers (Isolation).
        """
        CustomerFactory(organization=tenant_a, external_id="client_A_001")

        url = reverse("customers-list")
        api_client.credentials(HTTP_X_API_KEY=api_key_b)

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

        api_client.credentials(HTTP_X_API_KEY=api_key_a)
        response_a = api_client.get(url)
        assert len(response_a.data) == 1
        assert response_a.data[0]["external_id"] == "client_A_001"

    def test_end_to_end_accrual_and_redemption(self, api_client, tenant_a, api_key_a):
        """
        Scenario:
        1. Accrue 100 points via API.
        2. Verify Balance.
        3. Create a Reward (cost 40).
        4. Redeem (Buy) this Reward via API.
        5. Verify Balance is 60.
        """
        api_client.credentials(HTTP_X_API_KEY=api_key_a)
        customer_id = "user_flow_test"

        accrual_url = reverse("accruals-list")
        payload = {"external_id": customer_id, "amount": 100, "description": "Welcome Bonus"}

        response = api_client.post(accrual_url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        customer = Customer.objects.get(external_id=customer_id, organization=tenant_a)
        assert customer.get_balance() == 100
        from tests.factories.loyalty import RewardFactory

        reward = RewardFactory(organization=tenant_a, point_cost=40, name="Test Coffee")

        redemption_url = reverse("redemption-list")

        redeem_payload = {
            "customer_external_id": customer_id,
            "reward_id": reward.id,
        }

        response = api_client.post(redemption_url, redeem_payload, format="json")

        if response.status_code != 201:
            print(f"\nDEBUG ERROR RESPONSE: {response.data}")

        assert response.status_code == status.HTTP_201_CREATED

        customer.refresh_from_db()

        assert customer.get_balance() == 60

    def test_expiration_logic_complex_scenario(self, tenant_a):
        """
        Verifies the fix for the 'Double Counting' bug.

        Timeline setup:
        - 2022: Earn 100
        - 2023: Earn 100
        - 2024: Spend 50

        Expiration Check for target year 2022:
        - Earned(2022): 100
        - Lifetime Spent: 50
        - Should expire: 50
        """
        service = LoyaltyService()
        customer = CustomerFactory(organization=tenant_a, external_id="exp_test")

        # Use UTC for consistency
        tz = ZoneInfo("UTC")
        date_2022 = datetime(2022, 6, 1, 12, 0, 0, tzinfo=tz)
        date_2023 = datetime(2023, 6, 1, 12, 0, 0, tzinfo=tz)
        date_2024 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=tz)

        t1 = TransactionFactory(customer=customer, amount=100, transaction_type=Transaction.EARN)
        t1.created_at = date_2022
        t1.save(update_fields=["created_at"])

        t2 = TransactionFactory(customer=customer, amount=100, transaction_type=Transaction.EARN)
        t2.created_at = date_2023
        t2.save(update_fields=["created_at"])

        t3 = TransactionFactory(customer=customer, amount=-50, transaction_type=Transaction.SPEND)
        t3.created_at = date_2024
        t3.save(update_fields=["created_at"])

        customer.refresh_from_db()

        # Sanity Check: Balance should be 150 (200 earned - 50 spent)
        assert customer.get_balance() == 150

        # 2. Run Expiration for 2022
        # Logic: 100 earned in 2022. 50 spent total.
        # Remaining from 2022 to expire = 100 - 50 = 50.
        expired_amount = service.process_yearly_expiration(customer, target_year=2022)

        assert expired_amount == 50

        # Verify balance after expiration (150 - 50 = 100)
        # Refresh again because service did an update
        customer.refresh_from_db()
        assert customer.get_balance() == 100

        # 3. Future Check for 2023 (Theoretical)
        # If we check 2023 later, we have:
        # Earned 2023: 100
        # Earned Prior (2022): 100
        # Total Burned (Spend 50 + Expired 50): 100
        # Remaining Capacity: 100 (burned) - 100 (prior) = 0.
        # So NOTHING covers 2023 points. All 100 should expire.

        expired_2023 = service.process_yearly_expiration(customer, target_year=2023)
        assert expired_2023 == 100
