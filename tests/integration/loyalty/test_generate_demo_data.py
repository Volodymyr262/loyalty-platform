"""
Integration tests for the 'generate_demo_data' management command.
"""

from django.core.management import call_command
from django.utils import timezone

from loyalty.models import Customer, Transaction
from users.models import Organization


class TestGenerateDemoDataCommand:
    def test_creates_organization_if_none_exists(self):
        """
        Test that the command creates a default organization if the DB is empty.
        """
        assert Organization.objects.count() == 0

        call_command("generate_demo_data", customers=5, transactions=10, stdout=None)

        assert Organization.objects.count() == 1
        org = Organization.objects.first()
        assert org.name == "Demo Corp"

    def test_uses_existing_organization(self):
        """
        Test that the command reuses an existing organization instead of creating a duplicate.
        """
        existing_org = Organization.objects.create(name="Existing Corp")

        call_command("generate_demo_data", customers=5, transactions=10, stdout=None)

        assert Organization.objects.count() == 1
        assert Customer.objects.first().organization == existing_org

    def test_populates_customers_and_transactions(self):
        """
        Test that the correct number of customers and transactions are created.
        """
        call_command("generate_demo_data", customers=5, transactions=10, stdout=None)

        # Check counts based on the hardcoded values in your script
        assert Customer.objects.count() == 5
        assert Transaction.objects.count() == 10

    def test_transactions_are_backdated(self):
        """
        Test the logic that updates 'created_at' to be in the past.
        If the hack didn't work, all transactions would have the exact same timestamp (now).
        """
        call_command("generate_demo_data", customers=5, transactions=10, stdout=None)

        dates = list(Transaction.objects.values_list("created_at", flat=True)[:100])

        unique_dates = set(dates)
        assert len(unique_dates) > 1, "All transactions have the same timestamp! Backdating logic failed."

        now = timezone.now()
        recent_cutoff = now - timezone.timedelta(minutes=1)

        old_transactions_count = Transaction.objects.filter(created_at__lt=recent_cutoff).count()

        assert old_transactions_count > 6
