"""
Concurrency tests to demonstrate Race Conditions.
"""

import threading

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase

from core.context import set_current_organization_id
from loyalty.services import LoyaltyService
from tests.factories.loyalty import CustomerFactory, TransactionFactory


class TestRaceCondition(TransactionTestCase):
    """
    Uses threads to simulate concurrent requests.
    Using TransactionTestCase is crucial here because standard TestCase
    wraps everything in a transaction that rolls back, which hides concurrency issues.
    """

    def test_race_condition_double_spend_vulnerability(self):
        """
        Scenario: Customer has 100 points.
        Two threads try to spend 80 points AT THE SAME EXACT TIME.

        Expected (Vulnerable Code): Both succeed. Balance becomes -60.
        Expected (Protected Code): One succeeds, one fails. Balance becomes 20.
        """
        # 1. Setup
        customer = CustomerFactory()
        set_current_organization_id(customer.organization.id)
        service = LoyaltyService()

        # Initial Balance: 100
        TransactionFactory(customer=customer, amount=100)

        # Ensure DB is consistent before threads start
        connection.close()

        # 2. Define the worker function that threads will run
        def spend_points():
            # We create a new connection for each thread to simulate real concurrent requests
            # (Django handles this automatically in views, but in tests we need to be careful)
            try:
                service.process_transaction(customer, -80, "Concurrent Spend")
            except ValidationError:
                # This is expected if the code IS protected
                pass
            finally:
                connection.close()

        # 3. Create two threads
        t1 = threading.Thread(target=spend_points)
        t2 = threading.Thread(target=spend_points)

        # 4. Start them simultaneously
        t1.start()
        t2.start()

        # 5. Wait for both to finish
        t1.join()
        t2.join()

        # 6. Check the result
        customer.refresh_from_db()
        final_balance = customer.get_balance()

        print(f"\n[RACE TEST] Final Balance: {final_balance}")

        # ASSERTION FOR VULNERABILITY (This confirms your code IS broken)
        # If the balance is -60, it means both threads read "100" and both subtracted 80.
        # If your code was safe, the balance would be 20.
        if final_balance < 0:
            print("❌ RACE CONDITION DETECTED! Both transactions succeeded.")
            print("Your code is currently VULNERABLE.")
        else:
            print("✅ Code is SAFE. One transaction was blocked.")

        # This assert will FAIL if your code is vulnerable
        # We expect 20, but we will get -60.
        self.assertEqual(final_balance, 20, f"Race condition occurred! Balance is {final_balance} instead of 20")
