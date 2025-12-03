"""
Serializers for the Loyalty application.
"""

from rest_framework import serializers

from loyalty.models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    """
    Serializer for the Campaign model.
    """

    class Meta:
        model = Campaign
        fields = ["id", "name", "description", "points_value", "is_active"]
