"""
Script to generate demo data for the Loyalty Platform.
"""

import os
import random
import django
from datetime import timedelta
from django.utils import timezone


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import Organization
from loyalty.models import Customer, Transaction

def run():
    print(" Starting demo data generation...")

    org = Organization.objects.first()
    if not org:
        print("Creating new organization 'Demo Corp'...")
        org = Organization.objects.create(name="Demo Corp")

    print(f" Using organization: {org.name} (ID: {org.id})")

    print(" Generating 100 customers...")
    customers = []

    # Clear existing customers
    # Customer.objects.filter(organization=org).delete()

    for i in range(1, 101):
        unique_id = f"{i}_{random.randint(1000, 9999)}"
        email = f"customer_{unique_id}@example.com"
        external_id = f"DEMO_USER_{unique_id}"

        customer, created = Customer.objects.get_or_create(
            email=email,
            organization=org,
            defaults={
                'external_id': external_id
            }
        )
        customers.append(customer)

    print(f" Created/Found {len(customers)} customers.")

    # STEP 3: Generate 5000 Transactions ---
    print(" Generating 5000 transactions for the last 30 days...")

    # Optional: Clear old transactions
    Transaction.objects.all().delete()

    transactions_to_create = []
    now = timezone.now()

    TYPES = [Transaction.EARN, Transaction.SPEND]

    for _ in range(5000):
        customer = random.choice(customers)

        tx_type = random.choices(TYPES, weights=[80, 20], k=1)[0]

        days_ago = random.randint(0, 30)
        random_time = timedelta(
            days=days_ago,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        fake_date = now - random_time

        if tx_type == Transaction.EARN:
            amount = random.randint(10, 500)
        else:
            amount = random.randint(-400, -10)

        transaction = Transaction(
            customer=customer,
            organization=org,
            amount=amount,
            transaction_type=tx_type,
            description="Demo Data Auto-generated"
        )

        transaction.temp_date = fake_date

        transactions_to_create.append(transaction)

    print("⏳ Saving transactions to DB (this might take a few seconds)...")

    count = 0
    total = len(transactions_to_create)

    for tx in transactions_to_create:
        tx.save()
        Transaction.objects.filter(id=tx.id).update(created_at=tx.temp_date)

        count += 1
        if count % 1000 == 0:
            print(f"   ...processed {count}/{total}")

    print(f" Successfully created {total} transactions!")
    print(" Now go to /api/loyalty/stats/ and enjoy your charts!")

if __name__ == '__main__':
    run()