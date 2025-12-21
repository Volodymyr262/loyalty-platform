"""
Integration tests for TenantContextMiddleware.
"""

from django.http import HttpResponse
from django.test import RequestFactory

from core.context import get_current_organization_id
from core.middleware import TenantContextMiddleware
from tests.factories.users import OrganizationFactory


def dummy_view(request):
    """Simple view for tests that don't care about context internals."""
    return HttpResponse("OK")


class TestTenantMiddleware:
    """
    Test suite for the tenant authentication middleware.
    """

    def test_missing_header_returns_401(self):
        factory = RequestFactory()
        request = factory.get("/api/loyalty/resource/")

        middleware = TenantContextMiddleware(dummy_view)
        response = middleware(request)

        assert response.status_code == 401
        assert "Organization context required" in response.content.decode()

    def test_invalid_api_key_returns_403(self):
        factory = RequestFactory()
        request = factory.get("/api/loyalty/resource/", HTTP_X_TENANT_API_KEY="invalid-key")

        middleware = TenantContextMiddleware(dummy_view)
        response = middleware(request)

        assert response.status_code == 403
        assert "Invalid" in response.content.decode()

    def test_valid_api_key_sets_context(self):
        """
        Scenario: The client sends a valid API key.
        Expected: The context is set WHILE the view is executing.
        """
        # Arrange
        org = OrganizationFactory(api_key="secret-key-123")
        factory = RequestFactory()
        request = factory.get("/api/loyalty/resource/", HTTP_X_TENANT_API_KEY="secret-key-123")

        captured_org_id = None

        def spy_view(request):
            nonlocal captured_org_id
            # Capture the ID while the middleware "gate" is still open
            captured_org_id = get_current_organization_id()
            return HttpResponse("OK")

        # Act
        middleware = TenantContextMiddleware(spy_view)
        response = middleware(request)

        # Assert
        assert response.status_code == 200
        # Verify that INSIDE the view, the ID was correct
        assert captured_org_id == org.id

        # Verify that AFTER the request, context is cleaned up (Safety)
        assert get_current_organization_id() is None

    def test_malformed_jwt_token_is_ignored_by_middleware(self):
        """
        Scenario: Authorization header contains garbage.
        Expected: Middleware catches the error and user remains Anonymous.
        """
        factory = RequestFactory()
        # Not a valid JWT, just random string
        request = factory.get("/api/public/", HTTP_AUTHORIZATION="Bearer invalid.garbage.token")

        # Simulating middleware call
        middleware = TenantContextMiddleware(dummy_view)
        response = middleware(request)

        assert response.status_code == 200
        # Check that user is not set or is anonymous
        # getattr is safe if 'user' was never set
        user = getattr(request, "user", None)
        assert user is None or not user.is_authenticated
