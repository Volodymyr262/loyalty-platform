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
    Integration tests for Authentication endpoints (Registration, Login, Profile).
    """

    def setup_method(self):
        self.client = APIClient()

    def test_register_tenant_success(self):
        """
        POST /api/auth/register/
        Should create a new User, a new Organization, and return JWT tokens.
        """
        payload = {
            "email": "new_owner@coffee.com",
            "password": "StrongPassword123!",
            "organization_name": "Lviv Croissants",
        }

        url = "/api/auth/register/"
        response = self.client.post(url, data=payload)

        assert response.status_code == status.HTTP_201_CREATED

        data = response.data
        assert "access" in data
        assert "refresh" in data
        assert "organization" in data

        user = User.objects.get(email="new_owner@coffee.com")
        organization = Organization.objects.get(name="Lviv Croissants")

        assert user.organization == organization

    def test_register_duplicate_email_fails(self):
        """
        POST /api/auth/register/
        Should fail with 400 Bad Request if the email is already taken.
        """
        UserFactory(email="taken@email.com")
        payload = {"email": "taken@email.com", "password": "new_pass", "organization_name": "New Biz"}

        response = self.client.post("/api/auth/register/", data=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_gives_jwt_tokens(self):
        """
        POST /api/auth/login/
        Should return access and refresh tokens for valid credentials.
        """
        password = "password123"
        user = UserFactory(email="login@test.com")
        user.set_password(password)
        user.save()

        payload = {"email": "login@test.com", "password": password}
        response = self.client.post("/api/auth/login/", data=payload)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_invalid_credentials_fails(self):
        """
        POST /api/auth/login/
        Should return 401 Unauthorized for incorrect passwords.
        """
        user = UserFactory(email="hacker@test.com")
        user.set_password("correct_password")
        user.save()

        payload = {"email": "hacker@test.com", "password": "WRONG_PASSWORD"}
        response = self.client.post("/api/auth/login/", data=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_flow(self):
        """
        POST /api/auth/refresh/
        Should allow generating a new access token using a valid refresh token.
        """
        user = UserFactory()
        user.set_password("pass")
        user.save()

        # 1. Login to get initial tokens
        login_resp = self.client.post("/api/auth/login/", data={"email": user.email, "password": "pass"})
        refresh_token = login_resp.data["refresh"]

        # 2. Use refresh token to get new access token
        refresh_payload = {"refresh": refresh_token}
        response = self.client.post("/api/auth/refresh/", data=refresh_payload)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_get_current_user_profile(self):
        """
        GET /api/auth/me/
        Should return the current authenticated user's profile and organization details.
        """
        user = UserFactory(first_name="John", last_name="Doe")
        user.organization.name = "My Coffee Shop"
        user.organization.save()

        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/me/")

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["email"] == user.email
        assert data["organization"]["name"] == "My Coffee Shop"
        # API Key should not be exposed here

    def test_add_team_member_to_existing_org(self):
        """
        POST /api/auth/team/
        Should add a new user to the *same* organization as the requestor.
        """
        owner = UserFactory(email="owner@cafe.com")
        my_org = owner.organization
        self.client.force_authenticate(user=owner)

        payload = {"email": "manager@cafe.com", "password": "securepassword", "first_name": "Bob"}
        response = self.client.post("/api/auth/team/", data=payload)

        assert response.status_code == status.HTTP_201_CREATED

        new_employee = User.objects.get(email="manager@cafe.com")
        assert new_employee.organization == my_org
