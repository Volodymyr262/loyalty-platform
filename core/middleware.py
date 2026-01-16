"""
Middleware for handling tenant authentication and context management.
"""

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.context import reset_current_organization_id, set_current_organization_id
from users.models import OrganizationApiKey


class TenantContextMiddleware:
    """
    Acts as a "Gatekeeper". It determines the current Organization context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reset_current_organization_id()

        path = request.path
        # Skip authentication for admin, static files, auth endpoints, and docs
        if (
            path.startswith("/admin/")
            or path.startswith("/static/")
            or path.startswith("/media/")
            or path.startswith("/api/auth/")
            or "/api/docs/" in path
            or "/api/schema/" in path
            or "/favicon.ico" in path
        ):
            return self.get_response(request)

        organization = None

        # 1. Check for API Key (Machine-to-Machine)
        api_key = (
            request.headers.get("X-API-KEY")
            or request.headers.get("X-Tenant-API-Key")
            or request.headers.get("HTTP_X_API_KEY")
        )

        if api_key:
            try:
                # Optimized query to fetch organization along with the key
                key_obj = OrganizationApiKey.objects.select_related("organization").get(key=api_key, is_active=True)
                organization = key_obj.organization
            except OrganizationApiKey.DoesNotExist:
                return JsonResponse(
                    {"detail": "Invalid or inactive Tenant API Key."},
                    status=403,
                )

        # 2. Check for User Authentication (Human-to-Machine)
        else:
            user = getattr(request, "user", None)
            is_authenticated = user and user.is_authenticated

            # If user is not authenticated by Django yet, try manual JWT auth
            if not is_authenticated:
                try:
                    auth_result = JWTAuthentication().authenticate(request)
                    if auth_result:
                        user_obj, _ = auth_result
                        request.user = user_obj
                        user = user_obj
                except Exception:
                    # Ignore auth errors here; allow anonymous access if view permits,
                    # or block later if organization context is required.
                    pass

            user = getattr(request, "user", None)

            if user and user.is_authenticated:
                organization = user.organization

        # 3. Final Context Setup & Blocking
        # Block access to loyalty API if no organization context is found
        if path.startswith("/api/loyalty/") and not organization:
            return JsonResponse(
                {
                    "detail": "Organization context required. "
                    "Provide X-API-KEY header OR login as a user belonging to an organization."
                },
                status=401,
            )

        if organization:
            set_current_organization_id(organization.id)
            request.tenant = organization

            if hasattr(request, "user"):
                request.user.organization = organization

        response = self.get_response(request)
        reset_current_organization_id()

        return response
