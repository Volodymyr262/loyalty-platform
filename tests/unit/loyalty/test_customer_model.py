"""
Unit tests for the Customer model.
"""

import pytest
from django.core.cache import cache
from django.db import IntegrityError

from core.context import set_current_organization_id
from core.models import TenantAwareModel
from loyalty.models import Customer
from tests.factories.users import OrganizationFactory


@pytest.mark.django_db
class TestCustomerModel:
    """
    Tests for the Customer entity (the end-user/shopper).
    """

    def test_customer_inheritance(self):
        """
        Verify that Customer inherits from TenantAwareModel.
        """
        assert issubclass(Customer, TenantAwareModel)

    def test_create_customer_happy_path(self):
        """
        Verify we can create a customer record linked to a tenant.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        customer = Customer.objects.create(external_id="user_12345")

        assert customer.id is not None
        assert customer.external_id == "user_12345"
        assert customer.organization == org
        assert "user_12345" in str(customer)

    def test_external_id_uniqueness_within_organization(self):
        """
        CRITICAL: Verify that we cannot have two customers with the same external_id
        within the SAME organization.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        Customer.objects.create(external_id="duplicate_id")

        with pytest.raises(IntegrityError):
            Customer.objects.create(external_id="duplicate_id")

    def test_external_id_allowed_in_different_tenants(self):
        """
        Verify that the SAME external_id can exist in DIFFERENT organizations.
        (Shop A has customer '1', Shop B has customer '1').
        """
        org_a = OrganizationFactory()
        org_b = OrganizationFactory()

        set_current_organization_id(org_a.id)
        Customer.objects.create(external_id="user_1")

        set_current_organization_id(org_b.id)
        customer_b = Customer.objects.create(external_id="user_1")

        assert customer_b.pk is not None
        assert customer_b.organization == org_b

    def test_get_balance_calculates_sum_of_transactions(self):
        """
        Verify that get_balance() returns the correct sum of all transactions.
        """
        from loyalty.models import Transaction

        org = OrganizationFactory()
        set_current_organization_id(org.id)

        # Create a customer
        customer = Customer.objects.create(external_id="balance_test_user")

        #  Check initial balance (should be 0)
        assert customer.get_balance() == 0

        # 3. Add transactions (+100, -30, +10)
        Transaction.objects.create(customer=customer, amount=100, transaction_type="earn", organization=org)
        Transaction.objects.create(customer=customer, amount=-30, transaction_type="spend", organization=org)
        Transaction.objects.create(customer=customer, amount=10, transaction_type="earn", organization=org)

        cache.clear()
        # Verify calculated balance (100 - 30 + 10 = 80)
        assert customer.get_balance() == 80
