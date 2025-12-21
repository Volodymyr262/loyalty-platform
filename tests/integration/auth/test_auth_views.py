"""
Integration tests for Authentication (JWT + Registration).
"""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.users import UserFactory
from users.models import Organization

User = get_user_model()


class TestAuthAPI:
    """
    Tests for Registration and Login logic.
    """

    def setup_method(self):
        self.client = APIClient()

    def test_register_tenant_success(self):
        """
        POST /api/auth/register/
        Should create User, Organization, and return JWT tokens.
        """
        payload = {
            "email": "new_owner@coffee.com",
            "password": "StrongPassword123!",
            "organization_name": "Lviv Croissants",
        }

        url = "/api/auth/register/"

        response = self.client.post(url, data=payload)

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED

        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert "organization" in data

        # DB checks
        user = User.objects.get(email="new_owner@coffee.com")
        organization = Organization.objects.get(name="Lviv Croissants")

        assert user.organization == organization
        assert organization.api_key is not None

    def test_register_duplicate_email_fails(self):
        """
        Registration should fail if email already exists.
        """
        UserFactory(email="taken@email.com")

        payload = {"email": "taken@email.com", "password": "new_pass", "organization_name": "New Biz"}

        response = self.client.post("/api/auth/register/", data=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_login_gives_jwt_tokens(self):
        """
        POST /api/auth/login/
        Standard JWT login.
        """
        password = "password123"
        user = UserFactory(email="login@test.com")

        user.set_password(password)
        user.save()

        payload = {"email": "login@test.com", "password": password}
        response = self.client.post("/api/auth/login/", data=payload)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_invalid_credentials_fails(self):
        """
        POST /api/auth/login/
        Should return 401 Unauthorized for wrong password.
        """
        # Setup
        user = UserFactory(email="hacker@test.com")
        user.set_password("correct_password")
        user.save()

        # Attack with wrong password
        payload = {"email": "hacker@test.com", "password": "WRONG_PASSWORD"}
        response = self.client.post("/api/auth/login/", data=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "access" not in response.data

    def test_token_refresh_flow(self):
        """
        POST /api/auth/refresh/
        Should return a new access token using a valid refresh token.
        This is critical for "Keep me logged in" functionality.
        """
        user = UserFactory()
        user.set_password("pass")
        user.save()

        # Log in first to get the refresh token
        login_resp = self.client.post("/api/auth/login/", data={"email": user.email, "password": "pass"})
        refresh_token = login_resp.data["refresh"]

        #  Try to refresh the access token
        refresh_payload = {"refresh": refresh_token}
        response = self.client.post("/api/auth/refresh/", data=refresh_payload)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        # Refresh token might be rotated (new one returned) or kept the same depends on settings,
        # but access token MUST be there.

    def test_get_current_user_profile(self):
        """
        GET /api/auth/me/
        Should return details about the logged-in user and their organization.
        Frontend uses this to display "Welcome, Cafe Aroma!".
        """
        user = UserFactory(first_name="John", last_name="Doe")
        # Ensure organization has a name for verification
        user.organization.name = "My Coffee Shop"
        user.organization.save()

        # Authenticate the request
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["email"] == user.email
        assert data["first_name"] == "John"

        assert "organization" in data
        assert data["organization"]["name"] == "My Coffee Shop"
        assert "api_key" in data["organization"]

    def test_add_team_member_to_existing_org(self):
        """
        POST /api/auth/team/
        Should create a new user linked to the SAME organization as the requestor.
        """
        owner = UserFactory(email="owner@cafe.com")
        my_org = owner.organization

        self.client.force_authenticate(user=owner)

        payload = {"email": "manager@cafe.com", "password": "securepassword", "first_name": "Bob"}

        url = "/api/auth/team/"
        response = self.client.post(url, data=payload)

        assert response.status_code == status.HTTP_201_CREATED

        new_employee = User.objects.get(email="manager@cafe.com")

        assert new_employee.organization == my_org
        assert new_employee.organization.id == owner.organization.id

        assert Organization.objects.count() == 1
