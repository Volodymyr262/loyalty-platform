"""
Custom management command to generate demo data.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from loyalty.models import Customer, Transaction
from users.models import Organization


class Command(BaseCommand):
    help = "Generates demo data for the Loyalty Platform"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=100, help="Number of customers to generate")
        parser.add_argument("--transactions", type=int, default=5000, help="Number of transactions to generate")

    def handle(self, *args, **options):
        num_customers = options["customers"]
        num_transactions = options["transactions"]

        self.stdout.write(f" Starting demo data generation (Customers: {num_customers}, Tx: {num_transactions})...")

        org = Organization.objects.first()
        if not org:
            org = Organization.objects.create(name="Demo Corp")

        customers = []
        for i in range(1, num_customers + 1):
            unique_id = f"{i}_{random.randint(1000, 9999)}"
            customer, _ = Customer.objects.get_or_create(
                organization=org,
                external_id=f"DEMO_USER_{unique_id}",
                defaults={"email": f"customer_{unique_id}@example.com"},
            )
            customers.append(customer)

        transactions_to_create = []
        now = timezone.now()
        TYPES = [Transaction.EARN, Transaction.SPEND]

        for _ in range(num_transactions):
            customer = random.choice(customers)

            tx_type = random.choices(TYPES, weights=[80, 20], k=1)[0]

            if tx_type == Transaction.EARN:
                amount = random.randint(10, 500)
            else:
                amount = random.randint(-400, -10)

            tx = Transaction(
                customer=customer,
                organization=org,
                amount=amount,
                transaction_type=tx_type,
                description="Demo Data Auto-generated",
            )

            tx._temp_created_at = now - timedelta(days=random.randint(0, 30))

            transactions_to_create.append(tx)

        created_transactions = Transaction.objects.bulk_create(transactions_to_create)

        print(" Backdating transactions timestamps...")
        for tx in created_transactions:
            Transaction.objects.filter(id=tx.id).update(created_at=tx._temp_created_at)

        self.stdout.write(
            self.style.SUCCESS(f" Done! Created {num_customers} customers and {num_transactions} transactions.")
        )
