"""
Middleware for handling tenant authentication and context management.
"""

from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.context import reset_current_organization_id, set_current_organization_id
from users.models import OrganizationApiKey
import sys

def debug_print(msg):
    print(f"[MIDDLEWARE-DEBUG] {msg}", file=sys.stderr, flush=True)

class TenantContextMiddleware:
    """
    Acts as a "Gatekeeper". It determines the current Organization context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reset_current_organization_id()

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

        debug_print(f"Processing request: {path}")

        # Check for API Key (Machine-to-Machine)
        api_key = (
            request.headers.get("X-API-KEY")
            or request.headers.get("X-Tenant-API-Key")
            or request.headers.get("HTTP_X_API_KEY")
        )

        if api_key:
            debug_print("Found X-API-KEY")
            try:
                key_obj = OrganizationApiKey.objects.get(key=api_key, is_active=True)
                organization = key_obj.organization
                debug_print(f"API Key valid. Org: {organization.name}")
            except OrganizationApiKey.DoesNotExist:
                debug_print("API Key Invalid")
                return JsonResponse(
                    {"detail": "Invalid or inactive Tenant API Key."},
                    status=403,
                )

        # Check for User Authentication (Human-to-Machine)
        else:
            user = getattr(request, "user", None)
            is_authenticated = user and user.is_authenticated

            if not is_authenticated:
                # --- DEBUG: Show raw header ---
                auth_header = request.headers.get('Authorization')
                debug_print(f"User not authenticated. Authorization header: {auth_header}")

                try:
                    debug_print("Attempting manual JWT auth...")
                    auth_result = JWTAuthentication().authenticate(request)
                    if auth_result:
                        user_obj, _ = auth_result
                        # --- DEBUG: Show who was found ---
                        debug_print(f"JWT Success! User ID: {user_obj.id}, Email: {user_obj.email}")

                        request.user = user_obj
                        user = user_obj
                    else:
                        debug_print("JWT returned None (Header format might be wrong or token invalid)")
                except Exception as e:
                    debug_print(f"JWT Error Exception: {str(e)}")
                    pass

            user = getattr(request, "user", None)

            if user and user.is_authenticated:
                # --- DEBUG: Check Organization field ---
                org_val = getattr(user, 'organization', 'MISSING FIELD')
                debug_print(f"User is authenticated. Organization field value: {org_val}")
                organization = user.organization
            else:
                 debug_print("User remains Anonymous after checks.")

        # Final Context Setup
        if path.startswith("/api/loyalty/") and not organization:
            # --- DEBUG: Final Blocking Reason ---
            debug_print(f"BLOCKING REQUEST. Path: {path}. Reason: Organization is None.")
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
            debug_print(f"Context Set. Org ID: {organization.id}")

            if hasattr(request, "user"):
                request.user.organization = organization

        response = self.get_response(request)
        reset_current_organization_id()

        return response