"""
Unit tests for the Customer model.
"""

import pytest
from django.db import IntegrityError

from core.context import set_current_organization_id
from core.models import TenantAwareModel
from loyalty.models import Customer, Transaction
from tests.factories.loyalty import CustomerFactory, TransactionFactory
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
        """
        org_a = OrganizationFactory()
        org_b = OrganizationFactory()

        set_current_organization_id(org_a.id)
        Customer.objects.create(external_id="user_1")

        set_current_organization_id(org_b.id)
        customer_b = Customer.objects.create(external_id="user_1")

        assert customer_b.pk is not None
        assert customer_b.organization == org_b

    def test_get_balance_returns_stored_field(self):
        """
        FIXED: Verify that get_balance() returns the stored 'current_balance' field.
        We use TransactionFactory which has the 'magic' hook to update balance.
        """
        customer = CustomerFactory(current_balance=0)

        TransactionFactory(customer=customer, amount=100, transaction_type="earn")
        TransactionFactory(customer=customer, amount=-30, transaction_type="spend")
        TransactionFactory(customer=customer, amount=10, transaction_type="earn")

        customer.refresh_from_db()

        assert customer.get_balance() == 80
        assert customer.current_balance == 80

    def test_calculate_real_balance_audit(self):
        """
        NEW: Verify that the backup method 'calculate_real_balance' still works correctly
        by iterating over transactions sum (Audit/Reconciliation logic).
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        customer = Customer.objects.create(external_id="audit_test_user")

        # Create RAW transactions (bypassing Factory/Service logic).
        # This simulates a "broken" state where balance wasn't updated.
        Transaction.objects.create(customer=customer, amount=100, transaction_type="earn", organization=org)
        Transaction.objects.create(customer=customer, amount=-30, transaction_type="spend", organization=org)
        Transaction.objects.create(customer=customer, amount=10, transaction_type="earn", organization=org)

        # The field 'current_balance' is still 0 because we used raw create
        customer.refresh_from_db()
        assert customer.get_balance() == 0

        # BUT the audit method should find the real money
        assert customer.calculate_real_balance() == 80
