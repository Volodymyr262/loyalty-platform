"""
Celery tasks for Loyalty application.
"""

from celery import shared_task
from django.utils import timezone

from core.context import reset_current_organization_id, set_current_organization_id
from loyalty.models import Customer
from loyalty.services import LoyaltyService
from users.models import Organization


@shared_task
def process_organization_expiration(organization_id, target_year):
    """
    Worker Task: Processes expiration for a SINGLE organization.
    Crucial: Sets the context so TenantAwareManager works correctly.
    """
    set_current_organization_id(organization_id)

    try:
        customers = Customer.objects.iterator(chunk_size=1000)
        service = LoyaltyService()

        count = 0
        total_expired = 0

        for customer in customers:
            try:
                amount = service.process_yearly_expiration(customer, target_year)
                if amount > 0:
                    total_expired += amount
                    count += 1
            except Exception as e:
                # Log error specific to this customer, but don't stop the loop
                print(f"[Org {organization_id}] Error processing customer {customer.id}: {e}")

        return f"Org {organization_id}: Expired {total_expired} points for {count} customers."

    finally:
        # Always clean up context
        reset_current_organization_id()


@shared_task
def process_yearly_points_expiration():
    """
    Master Task (Dispatcher).
    Finds all active tenants and schedules a job for each.
    """
    today = timezone.now()
    target_year = today.year - 2

    active_org_ids = Organization.objects.filter(is_active=True).values_list("id", flat=True)

    print(f" Dispatching expiration tasks for {len(active_org_ids)} organizations. Target Year: {target_year}")

    for org_id in active_org_ids:
        process_organization_expiration.delay(org_id, target_year)

    return f"Dispatched {len(active_org_ids)} tasks."
