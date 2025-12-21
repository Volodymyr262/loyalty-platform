"""
API Views for the Loyalty application.
"""

from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from loyalty.models import Campaign, Customer, Reward, Transaction
from loyalty.serializers import (
    AccrualSerializer,
    CampaignSerializer,
    CustomerSerializer,
    RedemptionSerializer,
    RewardSerializer,
    TransactionReadSerializer,
)


class CampaignViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Campaigns.
    """

    permission_classes = [IsAuthenticated]

    serializer_class = CampaignSerializer

    def get_queryset(self):
        """
        Return the list of campaigns for the CURRENT tenant only.

        Because Campaign inherits from TenantAwareModel,
        Campaign.objects.all() is AUTOMATICALLY filtered by the current organization
        """
        return Campaign.objects.all()


class TransactionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/loyalty/transactions/
    Endpoint for transaction history.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionReadSerializer

    def get_queryset(self):
        return Transaction.objects.all().order_by("-created_at")


class AccrualViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    POST /api/loyalty/accruals/
    Endpoint for accrue (Earn).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AccrualSerializer


class RedemptionViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    """
    POST /api/loyalty/redemption/
    Endpoint for redemption (Spend).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RedemptionSerializer


class RewardViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Rewards (the catalog).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RewardSerializer

    def get_queryset(self):
        """
        Return rewards for the CURRENT tenant only.
        """
        return Reward.objects.all()


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Customers and their current balance.
    Creation is handled automatically via Accruals (Transactions).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CustomerSerializer

    # Enable search functionality (e.g., ?search=CLIENT_ID)
    filter_backends = [filters.SearchFilter]
    search_fields = ["external_id", "email"]

    def get_queryset(self):
        """
        Return customers belonging ONLY to the current tenant.
        """
        return Customer.objects.filter(organization=self.request.user.organization)
