"""
Unit tests for Loyalty Serializers.
"""

from loyalty.serializers import CampaignSerializer
from tests.factories.loyalty import CampaignFactory


class TestCampaignSerializer:
    """
    Test that Campaign model is correctly converted to JSON.
    """

    def test_campaign_serializer_contains_expected_fields(self):
        campaign = CampaignFactory(name="Test Campaign", points_value=100)

        serializer = CampaignSerializer(campaign)
        data = serializer.data

        assert data["id"] == campaign.id
        assert data["name"] == campaign.name
        assert data["points_value"] == 100

        assert "organization" not in data
