"""
Unit tests for Transaction model.
"""

from core.context import set_current_organization_id
from core.models import TenantAwareModel
from loyalty.models import Transaction
from tests.factories.loyalty import CustomerFactory
from tests.factories.users import OrganizationFactory


class TestTransactionModel:
    """
    Tests for the Transaction model (Ledger).
    """

    def test_transaction_inheritance(self):
        """
        Verify that Transaction inherits from TenantAwareModel.
        """
        assert issubclass(Transaction, TenantAwareModel)

    def test_create_earn_transaction(self):
        """
        Verify that we can create earn transaction successfully linked to a Customer.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        # Create a Customer instead of a User
        customer = CustomerFactory()

        transaction = Transaction.objects.create(
            customer=customer,
            amount=50,
            description="Bonus for registration",
            transaction_type="earn",
        )

        assert transaction.id is not None
        assert transaction.amount == 50
        assert transaction.customer == customer
        assert transaction.organization == org

    def test_create_spend_transaction(self):
        """
        Verify that we can create spend transaction successfully.
        """
        org = OrganizationFactory()
        set_current_organization_id(org.id)

        customer = CustomerFactory()

        transaction = Transaction.objects.create(
            customer=customer,
            amount=-50,
            description="Bought Coffee",
            transaction_type="spend",
        )

        assert transaction.id is not None
        assert transaction.amount == -50
        assert transaction.customer == customer
