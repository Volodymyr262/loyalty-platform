"""
Middleware for handling tenant authentication and context management.
Supports both API Key (for M2M) and JWT/Session (for Dashboard) authentication.
"""

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.context import reset_current_organization_id, set_current_organization_id
from users.models import Organization


class TenantContextMiddleware:
    """
    Acts as a "Gatekeeper". It determines the current Organization context using two strategies:
    1. 'X-Tenant-API-Key' header (External integrations, POS).
    2. Authenticated User's Organization (Admin Dashboard, Frontend).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Always reset context at the start of the request to prevent data leakage
        reset_current_organization_id()

        # 2. Define public paths that do not require tenant context
        path = request.path
        if (
            path.startswith("/admin/")
            or path.startswith("/static/")
            or path.startswith("/api/auth/")
            or "/api/docs/" in path
            or "/api/schema/" in path
            or "/favicon.ico" in path
        ):
            return self.get_response(request)

        organization = None

        # ---------------------------------------------------------------------
        # STRATEGY A: Check for API Key (Machine-to-Machine)
        # ---------------------------------------------------------------------
        api_key = request.headers.get("X-Tenant-API-Key") or request.headers.get("HTTP_X_TENANT_API_KEY")

        if api_key:
            try:
                organization = Organization.objects.get(api_key=api_key, is_active=True)
            except Organization.DoesNotExist:
                return JsonResponse(
                    {"detail": "Invalid or inactive Tenant API Key."},
                    status=403,
                )

        # ---------------------------------------------------------------------
        # STRATEGY B: Check for User Authentication (Human-to-Machine)
        # ---------------------------------------------------------------------
        else:
            # Safely check if 'user' attribute exists (it might be missing in tests using RequestFactory)
            user = getattr(request, "user", None)
            is_authenticated = user and user.is_authenticated

            # If user is not present or not authenticated, try manual JWT authentication
            if not is_authenticated:
                try:
                    # Manually attempt JWT authentication because Middleware runs BEFORE DRF Views
                    auth_result = JWTAuthentication().authenticate(request)
                    if auth_result:
                        user_obj, _ = auth_result
                        request.user = user_obj
                        user = user_obj
                except Exception:
                    # Ignore auth errors here; let the view handle 401 later if needed
                    pass

            # Re-fetch user safely after potential JWT auth
            user = getattr(request, "user", None)

            if user and user.is_authenticated:
                organization = user.organization

        # ---------------------------------------------------------------------
        # Final Context Setup
        # ---------------------------------------------------------------------

        # If we are accessing protected resources (Loyalty API) and still have no organization, block access.
        if path.startswith("/api/loyalty/") and not organization:
            return JsonResponse(
                {
                    "detail": "Organization context required. "
                    "Provide X-Tenant-API-Key header OR login as a user belonging to an organization."
                },
                status=401,
            )

        # If an organization was found, set the global context
        if organization:
            set_current_organization_id(organization.id)
            request.tenant = organization

            # If we authenticated via API Key, ensure request.user has the org context too.
            # We use hasattr to be safe in unit tests.
            if hasattr(request, "user"):
                request.user.organization = organization

        response = self.get_response(request)

        # Cleanup context after request
        reset_current_organization_id()

        return response
