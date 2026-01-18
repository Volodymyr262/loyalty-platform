"""
Tests for Organization API Key management endpoints.
"""

from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.users import OrganizationApiKeyFactory, OrganizationFactory, UserFactory
from users.models import OrganizationApiKey


class TestOrganizationApiKeyAPI:
    """
    Integration tests for managing Organization API Keys.
    Covers creation (revealing full key), listing (masked key), and deletion.
    """

    def setup_method(self):
        """
        Setup: Create a User with an Organization and authenticate.
        """
        self.client = APIClient()
        self.user = UserFactory()
        self.org = self.user.organization
        self.client.force_authenticate(user=self.user)

        self.url = "/api/auth/api-keys/"

    def test_create_api_key_returns_full_key(self):
        """
        POST /api/users/api-keys/
        Should create a new key and return the FULL (unmasked) key string
        in the response body so the user can save it.
        """
        payload = {"name": "POS Terminal 1"}

        response = self.client.post(self.url, data=payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "POS Terminal 1"

        key = response.data["key"]
        assert len(key) > 20
        assert "*" not in key

        assert OrganizationApiKey.objects.filter(organization=self.org, name="POS Terminal 1").exists()

    def test_list_api_keys_returns_masked_key(self):
        """
        GET /api/users/api-keys/
        Should return a list of keys, but the 'key' field must be masked (e.g., ****WXYZ).
        """
        raw_key = "sk_live_1234567890abcdef"
        OrganizationApiKeyFactory(organization=self.org, name="Website Key", key=raw_key)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

        item = response.data[0]
        assert item["name"] == "Website Key"

        # Verify masking logic
        masked_key = item["key"]
        assert masked_key != raw_key
        assert "****" in masked_key
        assert masked_key.endswith(raw_key[-4:])

    def test_tenant_isolation_for_api_keys(self):
        """
        GET /api/users/api-keys/
        Ensure we DO NOT see API keys belonging to other organizations.
        """
        # Create a key for THIS user's organization
        OrganizationApiKeyFactory(organization=self.org)

        other_org = OrganizationFactory()
        OrganizationApiKeyFactory(organization=other_org, name="Other Tenant Key")

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] != "Other Tenant Key"

    def test_delete_api_key(self):
        """
        DELETE /api/users/api-keys/{id}/
        Should revoke (delete) the API key permanently.
        """
        key_obj = OrganizationApiKeyFactory(organization=self.org)

        delete_url = f"{self.url}{key_obj.id}/"
        response = self.client.delete(delete_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        assert not OrganizationApiKey.objects.filter(id=key_obj.id).exists()

    def test_cannot_delete_other_org_key(self):
        """
        DELETE /api/users/api-keys/{id}/
        Attempting to delete another organization's key should return 404 (Not Found).
        """
        other_org = OrganizationFactory()
        other_key = OrganizationApiKeyFactory(organization=other_org)

        delete_url = f"{self.url}{other_key.id}/"
        response = self.client.delete(delete_url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        assert OrganizationApiKey.objects.filter(id=other_key.id).exists()

    def test_update_is_not_allowed(self):
        """
        PUT/PATCH /api/users/api-keys/{id}/
        Updating keys should be forbidden.
        """
        key_obj = OrganizationApiKeyFactory(organization=self.org)

        update_url = f"{self.url}{key_obj.id}/"
        payload = {"name": "New Name"}

        response = self.client.patch(update_url, data=payload)

        assert response.status_code in [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND]
