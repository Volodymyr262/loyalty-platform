"""
API Views for the Loyalty application.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from loyalty.models import Campaign, Transaction
from loyalty.serializers import CampaignSerializer, TransactionSerializer


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


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for processing Transactions (Accrual/Redemption).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Return transactions only for the current tenant.
        """
        return Transaction.objects.all()
