"""
Tests for Loyalty API Views.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from tests.factories.loyalty import CampaignFactory
from tests.factories.users import OrganizationApiKeyFactory, UserFactory


class TestCampaignAPI:
    """
    Integration tests for Campaign management endpoints.
    """

    def setup_method(self):
        """
        Setup: Create User, Organization, generate API Key, and set Auth headers.
        """
        self.client = APIClient()

        self.user = UserFactory()
        self.org = self.user.organization

        # Authenticate user (for DRF Permissions IsAuthenticated)
        self.client.force_authenticate(user=self.user)

        # Create API Key (for Middleware to determine Tenant Context)
        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

        set_current_organization_id(self.org.id)

    def test_list_campaigns(self):
        """
        GET /api/loyalty/campaigns/
        Ensure we see a list of campaigns belonging ONLY to our organization.
        """
        CampaignFactory(name="My Campaign 1", organization=self.org)
        CampaignFactory(name="My Campaign 2", organization=self.org)
        CampaignFactory(name="Stranger Campaign")

        url = "/api/loyalty/campaigns/"

        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_create_campaign(self):
        """
        POST /api/loyalty/campaigns/
        Should create a new campaign with basic fields.
        """
        payload = {
            "name": "Summer Sale",
            "description": "Double points for cold drinks",
            "points_value": 2,
            "is_active": True,
        }

        url = "/api/loyalty/campaigns/"
        response = self.client.post(url, data=payload, format="json", **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == payload["name"]

    def test_update_campaign(self):
        """
        PATCH /api/loyalty/campaigns/{id}/
        Should successfully update specific fields of a campaign.
        """
        campaign = CampaignFactory(name="Old Name", points_value=10, organization=self.org)

        url = f"/api/loyalty/campaigns/{campaign.id}/"
        payload = {"name": "New Name", "points_value": 20}

        response = self.client.patch(url, data=payload, format="json", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"

    def test_delete_campaign(self):
        """
        DELETE /api/loyalty/campaigns/{id}/
        Should successfully delete a campaign belonging to the tenant.
        """
        campaign = CampaignFactory(organization=self.org)
        url = f"/api/loyalty/campaigns/{campaign.id}/"

        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_delete_other_tenant_campaign(self):
        """
        DELETE /api/loyalty/campaigns/{id}/
        Attempting to delete another tenant's campaign should return 404 Not Found.
        """
        other_campaign = CampaignFactory(name="Stolen Campaign")
        url = f"/api/loyalty/campaigns/{other_campaign.id}/"

        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_campaign_with_rules(self):
        """
        POST /api/loyalty/campaigns/
        Should create a campaign with 'rules' JSON and specific reward type.
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
