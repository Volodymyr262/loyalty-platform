"""
Tests for Rewards API view
"""

from rest_framework import status
from rest_framework.test import APIClient

from core.context import set_current_organization_id
from loyalty.models import Reward
from tests.factories.loyalty import RewardFactory
from tests.factories.users import UserFactory


class TestRewardAPI:
    """
    Integration tests for Reward ViewSet.
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization

        # Authenticate and set context
        self.client.force_authenticate(user=self.user)
        self.headers = {"HTTP_X_TENANT_API_KEY": self.org.api_key}
        set_current_organization_id(self.org.id)

    def test_list_rewards_isolation(self):
        """
        GET /api/loyalty/rewards/
        Ensure we ONLY see rewards belonging to our organization.
        """
        # Create reward for OUR organization
        my_reward = RewardFactory(organization=self.org, name="My Free Coffee")

        # Create reward for ANOTHER organization
        other_user = UserFactory()
        RewardFactory(organization=other_user.organization, name="Stolen Cookie")

        response = self.client.get("/api/loyalty/rewards/", **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "My Free Coffee"
        assert response.data[0]["id"] == my_reward.id

    def test_create_reward(self):
        """
        POST /api/loyalty/rewards/
        Ensure we can create a reward and it gets assigned to our organization.
        """
        payload = {"name": "VIP Access", "description": "Access to VIP lounge", "point_cost": 500, "is_active": True}

        response = self.client.post("/api/loyalty/rewards/", data=payload, **self.headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "VIP Access"

        # DB Check
        reward = Reward.objects.get(id=response.data["id"])
        assert reward.organization == self.org
        assert reward.point_cost == 500

    def test_update_reward(self):
        """
        PATCH /api/loyalty/rewards/{id}/
        Ensure we can update price or name.
        """
        reward = RewardFactory(organization=self.org, point_cost=100)

        url = f"/api/loyalty/rewards/{reward.id}/"
        payload = {"point_cost": 150}

        response = self.client.patch(url, data=payload, **self.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["point_cost"] == 150

        reward.refresh_from_db()
        assert reward.point_cost == 150

    def test_delete_reward_permissions(self):
        """
        DELETE /api/loyalty/rewards/{id}/
        Ensure we cannot delete another tenant's reward.
        """
        other_user = UserFactory()
        other_reward = RewardFactory(organization=other_user.organization)

        url = f"/api/loyalty/rewards/{other_reward.id}/"

        # Try to delete using OUR headers/auth
        response = self.client.delete(url, **self.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Reward.objects.filter(id=other_reward.id).exists()
