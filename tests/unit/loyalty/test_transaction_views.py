"""
Test for Transaction API endpoints.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Customer, Transaction
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
        assert response.data[0]["amount"] == 100
