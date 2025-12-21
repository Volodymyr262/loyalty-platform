"""
Tests for Loyalty API Views.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Campaign
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import UserFactory


class TestCampaignAPI:
    """
    Test the Campaign API endpoints.
    """

    def setup_method(self):
        """
        Runs before EACH test method.
        Sets up the User, Organization, and Authentication.
        """
        self.client = APIClient()

        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_TENANT_API_KEY": self.org.api_key}

        set_current_organization_id(self.org.id)

    def test_list_campaigns(self):
        """
        GET /api/loyalty/campaigns/ should return a list of campaigns.
        """
        CampaignFactory(name="My Campaign 1", organization=self.org)
        CampaignFactory(name="My Campaign 2", organization=self.org)
        CampaignFactory(name="Stranger Campaign")

        url = "/api/loyalty/campaigns/"

        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        expected_names = {"My Campaign 1", "My Campaign 2"}
        received_names = {c["name"] for c in response.data}
        assert received_names == expected_names

    def test_create_campaign(self):
        """
        POST /api/loyalty/campaigns/ should create a new campaign.
        It must automatically assign the current user's organization.
        """
        payload = {
            "name": "Summer Sale",
            "description": "Double points for cold drinks",
            "points_value": 2,  # Integer, бо ми змінили модель на PositiveIntegerField
            "is_active": True,
        }

        url = "/api/loyalty/campaigns/"
        response = self.client.post(url, data=payload, format="json", **self.headers)

        assert response.status_code == status.HTTP_201_CREATED

        assert "id" in response.data
        assert response.data["name"] == payload["name"]

        created_campaign = Campaign.objects.get(id=response.data["id"])

        assert created_campaign.organization == self.org

    def test_update_campaign(self):
        """
        PATCH /api/loyalty/campaigns/{id}/ should update the campaign.
        """
        campaign = CampaignFactory(name="Old Name", points_value=10, organization=self.org)

        url = f"/api/loyalty/campaigns/{campaign.id}/"
        payload = {"name": "New Name", "points_value": 20}

        response = self.client.patch(url, data=payload, format="json", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"

        campaign.refresh_from_db()
        assert campaign.name == "New Name"
        assert campaign.points_value == 20

    def test_delete_campaign(self):
        """
        DELETE /api/loyalty/campaigns/{id}/ should remove the campaign.
        """
        campaign = CampaignFactory(organization=self.org)
        url = f"/api/loyalty/campaigns/{campaign.id}/"

        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert Campaign.objects.filter(id=campaign.id).exists() is False

    def test_cannot_delete_other_tenant_campaign(self):
        """
        Attempting to delete another tenant's campaign should return 404 Not Found.
        """
        other_campaign = CampaignFactory(name="Stolen Campaign")

        url = f"/api/loyalty/campaigns/{other_campaign.id}/"

        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert Campaign.objects.filter(id=other_campaign.id).exists() is True

    def test_create_campaign_with_rules(self):
        """
        POST /api/loyalty/campaigns/
        Should create a campaign with specific Rules and Reward Type.
        """
        payload = {
            "name": "Big Spender Bonus",
            "description": "Get +500 points for orders over 1000",
            "points_value": 500,
            "reward_type": "bonus",
            "rules": {"min_amount": 1000},
            "is_active": True,
        }

        url = "/api/loyalty/campaigns/"

        response = self.client.post(url, data=payload, format="json", **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["reward_type"] == "bonus"
        assert response.data["rules"] == {"min_amount": 1000}

        created_campaign = Campaign.objects.get(id=response.data["id"])

        assert created_campaign.reward_type == "bonus"
        assert created_campaign.rules["min_amount"] == 1000
        assert created_campaign.organization == self.org
