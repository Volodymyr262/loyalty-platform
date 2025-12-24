"""
Tests for Reward API endpoints.
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Reward
from tests.factories.loyalty import RewardFactory

# ДОДАЄМО OrganizationApiKeyFactory
from tests.factories.users import OrganizationApiKeyFactory, UserFactory


class TestRewardAPI:
    """
    Integration tests for Reward management endpoints.
    """

    def setup_method(self):
        """
        Setup: Create User, Organization, generate API Key, and set Auth headers.
        """
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)

        # Generate API Key for Middleware authentication
        api_key_obj = OrganizationApiKeyFactory(organization=self.org)
        self.headers = {"HTTP_X_API_KEY": api_key_obj.key}

        set_current_organization_id(self.org.id)

    def test_list_rewards_isolation(self):
        """
        GET /api/loyalty/rewards/
        Ensure we ONLY see rewards belonging to our organization (Multi-tenancy isolation).
        """
        RewardFactory(organization=self.org, name="My Reward")

        other_user = UserFactory()
        RewardFactory(organization=other_user.organization, name="Other Reward")

        url = "/api/loyalty/rewards/"
        response = self.client.get(url, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "My Reward"

    def test_create_reward(self):
        """
        POST /api/loyalty/rewards/
        Should create a new reward and automatically assign it to the current tenant.
        """
        payload = {"name": "Free Coffee", "description": "Delicious", "point_cost": 50, "is_active": True}
        url = "/api/loyalty/rewards/"
        response = self.client.post(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert Reward.objects.count() == 1
        assert Reward.objects.first().organization == self.org

    def test_update_reward(self):
        """
        PATCH /api/loyalty/rewards/{id}/
        Should update fields (e.g., point_cost) of an existing reward.
        """
        reward = RewardFactory(organization=self.org, point_cost=100)
        url = f"/api/loyalty/rewards/{reward.id}/"

        payload = {"point_cost": 150}
        response = self.client.patch(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        reward.refresh_from_db()
        assert reward.point_cost == 150

    def test_delete_reward_permissions(self):
        """
        DELETE /api/loyalty/rewards/{id}/
        - Should allow deleting own rewards (204 No Content).
        - Should return 404 Not Found when attempting to delete another tenant's reward.
        """
        # Check if user can delete their own reward
        reward = RewardFactory(organization=self.org)
        url = f"/api/loyalty/rewards/{reward.id}/"

        response = self.client.delete(url, **self.headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check attempting to delete another tenant's reward
        other_reward = RewardFactory(name="Other")
        url = f"/api/loyalty/rewards/{other_reward.id}/"

        response = self.client.delete(url, **self.headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
