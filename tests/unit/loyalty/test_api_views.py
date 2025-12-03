"""
Tests for Loyalty API Views.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
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

        set_current_organization_id(self.org.id)

    def test_list_campaigns(self):
        """
        GET /api/loyalty/campaigns/ should return a list of campaigns.
        """
        CampaignFactory(name="My Campaign 1", organization=self.org)
        CampaignFactory(name="My Campaign 2", organization=self.org)
        CampaignFactory(name="Stranger Campaign")

        url = "/api/loyalty/campaigns/"

        response = self.client.get(url, **{"HTTP_X_TENANT_API_KEY": self.org.api_key})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

        expected_names = {"My Campaign 1", "My Campaign 2"}
        received_names = {c["name"] for c in response.data}
        assert received_names == expected_names
