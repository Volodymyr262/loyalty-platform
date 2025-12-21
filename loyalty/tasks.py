from celery import shared_task
from django.utils import timezone

from loyalty.models import Customer
from loyalty.services import LoyaltyService


@shared_task
def process_yearly_points_expiration():
    """
    Periodic task to run the N+1 expiration strategy.
    Should be scheduled to run once a year (e.g., Jan 1st).
    """
    # Logic N+1:
    # if today 2026 , we expire points from 2024.
    # so points lifetime is at least 1 year
    today = timezone.now()
    target_year = today.year - 2

    print(f"Starting points expiration task for target year: {target_year}")

    batch_size = 1000
    service = LoyaltyService()

    processed_count = 0
    expired_points_total = 0

    # Using iterator() to reduce memory usage
    customers = Customer.objects.all().iterator(chunk_size=batch_size)

    for customer in customers:
        try:
            expired = service.process_yearly_expiration(customer, target_year)
            if expired > 0:
                expired_points_total += expired
                print(f"Expired {expired} points for Customer {customer.id}")
            processed_count += 1
        except Exception as e:
            print(f"Error processing customer {customer.id}: {e}")

    return f"Finished. Processed {processed_count} customers. Total expired: {expired_points_total}"
