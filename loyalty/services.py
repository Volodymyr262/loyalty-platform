"""
Service layer for Loyalty business logic.
Handles point calculations, validations, and transaction processing.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone as django_timezone

from loyalty.models import Campaign, Customer, Transaction


class LoyaltyService:
    """
    Encapsulates the rules for earning and spending points.
    """

    @transaction.atomic
    def process_transaction(
        self, customer, amount: int, description: str = "", transaction_type: str = None
    ) -> Transaction:
        """
        Safely processes a point transaction.

        Args:
            customer: The Customer instance.
            amount: Integer (positive to earn, negative to spend).
            description: Reason for the transaction.
            transaction_type: Optional override (e.g., for EXPIRATION).
                              If None, it is inferred from amount.

        Returns:
            The created Transaction object.
        """
        _ = Customer.objects.select_for_update().get(id=customer.id)

        # Determine Transaction Type
        if transaction_type:
            tx_type = transaction_type
        else:
            tx_type = Transaction.SPEND if amount < 0 else Transaction.EARN

        # Validation for spending
        if amount < 0:
            current_balance = customer.get_balance()
            if current_balance + amount < 0:
                raise ValidationError(f"Insufficient funds. Balance: {current_balance}, Required: {abs(amount)}")

        # Create Transaction
        new_transaction = Transaction.objects.create(
            customer=customer,
            amount=amount,
            transaction_type=tx_type,
            description=description,
            organization=customer.organization,
        )
        cache.delete(f"customer_balance:{customer.id}")
        return new_transaction

    def process_yearly_expiration(self, customer, target_year: int) -> int:
        """
        Expires points earned in `target_year` based on N+1 Strategy (Calendar Year).

        Logic (FIFO):
        We calculate if the user has enough 'old' points that haven't been spent yet.
        Formula: (Total Earned in Target Year) - (Total Lifetime Spent).

        Args:
            customer: The customer to check.
            target_year: The year to audit (e.g., 2023).

        Returns:
            int: The amount of points expired (positive integer).
        """

        cutoff_date = datetime(target_year, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)

        # Calculate Total Earned Points up to the end of the target year.
        # We include all previous years to be safe, assuming previous years were handled
        # by prior runs. If this is the first run, it effectively cleans up everything old.
        earned_aggregate = (
            Transaction.objects.filter(
                customer=customer, transaction_type=Transaction.EARN, created_at__lte=cutoff_date
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Calculate Total Spent/Expired Points (Lifetime).
        # We look at all spending ever occurred (even after the target year),
        # because customers always spend their "oldest" points first (FIFO).
        used_aggregate = (
            Transaction.objects.filter(
                customer=customer, transaction_type__in=[Transaction.SPEND, Transaction.EXPIRATION]
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # Convert negative spending to positive number for calculation
        total_used = abs(used_aggregate)

        # Calculate Remainder
        # Example: Earned 1000 in 2023. Spent 200 in 2024.
        # Points to expire = 1000 - 200 = 800.
        points_to_expire = earned_aggregate - total_used

        if points_to_expire > 0:
            # Create a negative transaction with specific type EXPIRATION
            self.process_transaction(
                customer=customer,
                amount=-points_to_expire,
                description=f"Expiration of points earned in {target_year}",
                transaction_type=Transaction.EXPIRATION,
            )
            return points_to_expire

        return 0


def get_active_campaigns(organization_id):
    """
    Retrieves active campaigns from Redis cache or Database.
    Cache key: 'active_campaigns:{organization_id}'
    TTL: 1 hour (3600 seconds).
    """
    cache_key = f"active_campaigns:{organization_id}"
    campaigns = cache.get(cache_key)

    if campaigns is None:
        campaigns = list(Campaign.objects.filter(organization_id=organization_id, is_active=True))
        cache.set(cache_key, campaigns, timeout=60 * 60)

    return campaigns


def calculate_points(amount, customer):
    """
    Calculates points based on Amount + Active Campaigns (Rules & Types).
    Uses cached campaigns to reduce DB hits.
    """
    amount_decimal = Decimal(amount)
    base_points = int(amount_decimal)
    best_points = base_points

    now = django_timezone.localtime(django_timezone.now())
    current_time = now.time()

    campaigns = get_active_campaigns(customer.organization.id)

    for campaign in campaigns:
        rules = campaign.rules or {}
        is_applicable = True

        # RULE 1: Min Amount
        if "min_amount" in rules:
            min_amount = Decimal(str(rules["min_amount"]))
            if amount_decimal < min_amount:
                is_applicable = False

        # RULE 2: Welcome Bonus (First Purchase)
        if "is_first_purchase" in rules and rules["is_first_purchase"] is True:
            if customer.transactions.exists():
                is_applicable = False

        # RULE 3: Happy Hours (Time Window)
        if "start_time" in rules and "end_time" in rules:
            try:
                # FIX: 'datetime' here refers to the imported class, which has strptime method
                start = datetime.strptime(rules["start_time"], "%H:%M").time()
                end = datetime.strptime(rules["end_time"], "%H:%M").time()

                if not (start <= current_time <= end):
                    is_applicable = False
            except ValueError:
                pass

        if not is_applicable:
            continue

        # Calculation
        calculated_points = base_points

        if campaign.reward_type == Campaign.TYPE_MULTIPLIER:
            calculated_points = int(amount_decimal * Decimal(campaign.points_value))

        elif campaign.reward_type == Campaign.TYPE_BONUS:
            calculated_points = base_points + campaign.points_value

        if calculated_points > best_points:
            best_points = calculated_points

    return best_points


class DashboardAnalyticsService:
    """
    Encapsulates logic for calculating Dashboard metrics.
    Decouples data extraction from API presentation.
    """

    @staticmethod
    def get_kpi(queryset):
        """
        Calculates high-level KPIs: Customers, Liability, Redemption Rate.
        """
        stats = queryset.aggregate(
            total_customers=Count("customer", distinct=True),
            total_issued=Coalesce(Sum("amount", filter=Q(transaction_type="earn")), 0),
            total_redeemed=Coalesce(Sum("amount", filter=Q(transaction_type="spend")), 0),
            current_liability=Coalesce(Sum("amount"), 0),
        )

        # Business Logic: Calculate Rate
        issued = stats["total_issued"]
        redeemed = abs(stats["total_redeemed"])

        redemption_rate = 0.0
        if issued > 0:
            redemption_rate = round((redeemed / issued) * 100, 1)

        return {
            "total_customers": stats["total_customers"],
            "current_liability": stats["current_liability"],
            "redemption_rate": redemption_rate,
        }

    @staticmethod
    def get_timeline(queryset, days=30):
        """
        Generates daily stats for charts (Last N days).
        """
        # FIX: Replaced timezone.now() with django_timezone.now()
        start_date = django_timezone.now() - timedelta(days=days)

        timeline_qs = (
            queryset.filter(created_at__gte=start_date)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                issued=Coalesce(Sum("amount", filter=Q(transaction_type="earn")), 0),
                redeemed=Coalesce(Sum("amount", filter=Q(transaction_type="spend")), 0),
            )
            .order_by("date")
        )

        # Formatting data for frontend
        return [
            {"date": entry["date"], "issued": entry["issued"], "redeemed": abs(entry["redeemed"])}
            for entry in timeline_qs
        ]
