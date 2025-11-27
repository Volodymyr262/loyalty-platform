"""
Middleware for handling tenant authentication and context management.
It acts as the "Gatekeeper", identifying the tenant by API Key.
"""

from django.http import JsonResponse

from core.context import reset_current_organization_id, set_current_organization_id
from users.models import Organization


class TenantContextMiddleware:
    """
    Extracts the X-Tenant-API-Key header from the request, validates it against
    active Organizations, and sets the global tenant context for the duration of the request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # This prevents data leakage in environments that reuse threads
        reset_current_organization_id()

        if request.path.startswith(("/admin/", "/schema/", "/api/schema/", "/health/")):
            return self.get_response(request)

        # Extract API Key from headers
        api_key = request.headers.get("X-Tenant-API-Key")

        if not api_key:
            return JsonResponse(
                {"detail": "X-Tenant-API-Key header is missing."},
                status=401,
            )

        # Lookup Organization in the database
        # We assume the key is unique (enforced by model) and the tenant must be active.
        try:
            organization = Organization.objects.get(api_key=api_key, is_active=True)
        except Organization.DoesNotExist:
            return JsonResponse(
                {"detail": "Invalid or inactive Tenant API Key."},
                status=403,
            )

        # Set the "Invisible Wall" context
        # Now any query executed by TenantAwareManager will automatically filter by this ID.
        set_current_organization_id(organization.id)

        # Attach tenant to request (Optional DX improvement)
        # This allows views to easily access `request.tenant` without querying DB again.
        request.tenant = organization

        # Continue processing the request
        response = self.get_response(request)

        # Cleanup (Optional but good practice)
        reset_current_organization_id()

        return response
