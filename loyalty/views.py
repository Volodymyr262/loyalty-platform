"""
API Views for the Loyalty application.
"""

from rest_framework import viewsets

from loyalty.models import Campaign
from loyalty.serializers import CampaignSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Campaigns.
    """

    # permission_classes = [IsAuthenticated]

    serializer_class = CampaignSerializer

    def get_queryset(self):
        """
        Return the list of campaigns for the CURRENT tenant only.

        Because Campaign inherits from TenantAwareModel,
        Campaign.objects.all() is AUTOMATICALLY filtered by the current organization
        """
        return Campaign.objects.all()
