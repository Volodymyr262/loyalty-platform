from rest_framework import authentication, exceptions

from users.models import OrganizationApiKey


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticates requests based on the 'X-API-KEY' header.
    """

    def authenticate(self, request):
        api_key_header = request.headers.get("X-API-KEY")

        if not api_key_header:
            return None  # Authentication not attempted

        try:
            api_key_obj = OrganizationApiKey.objects.get(key=api_key_header, is_active=True)
        except OrganizationApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid or inactive API Key.") from None

        from django.contrib.auth.models import AnonymousUser

        return (AnonymousUser(), api_key_obj)
