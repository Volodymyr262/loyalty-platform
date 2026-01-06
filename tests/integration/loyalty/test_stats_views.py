from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from tests.factories.loyalty import CustomerFactory, TransactionFactory
from tests.factories.users import OrganizationApiKeyFactory, UserFactory


class TestDashboardStatsAPI:
    """
    Integration tests for Dashboard Analytics (Stats Endpoint).
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)

        # Auth setup with API Key
        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

        set_current_organization_id(self.org.id)

        self.url = "/api/loyalty/stats/"

    def test_kpi_calculations(self):
        """
        Scenario:
        1. Customer A: Earns 100.
        2. Customer B: Earns 200.
        3. Customer A: Spends 60.

        Expected Math:
        - Total Customers: 2
        - Total Issued: 300 (100 + 200)
        - Total Redeemed: 60 (Absolute value)
        - Current Liability: 240 (300 - 60)
        - Redemption Rate: 20% (60 / 300 * 100)
        """
        c1 = CustomerFactory(organization=self.org)
        c2 = CustomerFactory(organization=self.org)

        #  Earn Transactions
        TransactionFactory(customer=c1, amount=100, transaction_type="earn")
        TransactionFactory(customer=c2, amount=200, transaction_type="earn")

        #  Spend Transaction (negative amount in DB)
        TransactionFactory(customer=c1, amount=-60, transaction_type="spend")

        # Act
        response = self.client.get(self.url, **self.headers)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        kpi = response.data["kpi"]

        assert kpi["total_customers"] == 2
        assert kpi["current_liability"] == 240.0
        assert kpi["redemption_rate"] == 20.0

    def test_timeline_date_grouping(self):
        """
        Scenario:
        - Transaction Today: Earn 50
        - Transaction Yesterday: Earn 50
        - Transaction Yesterday: Spend 20
        - Transaction 40 days ago: Earn 1000 (Should be ignored in timeline)
        """
        customer = CustomerFactory(organization=self.org)
        now = timezone.now()

        # Today
        _ = TransactionFactory(customer=customer, amount=50, transaction_type="earn")

        # Yesterday
        yesterday = now - timedelta(days=1)
        t2 = TransactionFactory(customer=customer, amount=50, transaction_type="earn")
        t2.created_at = yesterday
        t2.save()  # Update DB

        t3 = TransactionFactory(customer=customer, amount=-20, transaction_type="spend")
        t3.created_at = yesterday
        t3.save()

        # Old transaction (should not appear in chart)
        old_date = now - timedelta(days=40)
        t4 = TransactionFactory(customer=customer, amount=1000, transaction_type="earn")
        t4.created_at = old_date
        t4.save()

        # Act
        response = self.client.get(self.url, **self.headers)
        timeline = response.data["timeline"]

        # Assert
        # Should have data for Today and Yesterday.
        # Timeline might return empty days as well depending on implementation,
        # or just days with data. Our aggregation usually returns only days with data.

        # We expect 2 entries in timeline (Yesterday and Today), assuming grouping works
        # Depending on timezones, today and yesterday might fall into specific buckets,
        # but the key is that '1000' amount is NOT in the sum.

        total_issued_in_timeline = sum(item["issued"] for item in timeline)
        total_redeemed_in_timeline = sum(item["redeemed"] for item in timeline)

        assert total_issued_in_timeline == 100.0  # 50 today + 50 yesterday. (1000 ignored)
        assert total_redeemed_in_timeline == 20.0  # 20 yesterday

    def test_tenant_isolation(self):
        """
        Ensure KPIs do not include data from other organizations.
        """
        # Our data
        TransactionFactory(customer__organization=self.org, amount=100, transaction_type="earn")

        # Stranger's data
        other_user = UserFactory()
        TransactionFactory(customer__organization=other_user.organization, amount=5000, transaction_type="earn")

        # Act
        response = self.client.get(self.url, **self.headers)
        kpi = response.data["kpi"]

        # Assert
        assert kpi["current_liability"] == 100.0  # NOT 5100
