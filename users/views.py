"""
Authentication Views.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import OrganizationApiKey
from users.serializers import (
    OrganizationApiKeySerializer,
    TeamMemberSerializer,
    TenantRegistrationSerializer,
    UserDetailSerializer,
)


@extend_schema(tags=["auth"])
class RegisterTenantView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Public endpoint to register a new tenant (Organization + Owner).
    """

    permission_classes = [AllowAny]
    serializer_class = TenantRegistrationSerializer

    @extend_schema(summary="Register New Tenant", description="Creates a new Organization and an Owner user.")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["auth"])
class UserProfileView(APIView):
    """
    GET /api/auth/me/
    Returns details about the currently logged-in user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    @extend_schema(
        summary="Get My Profile",
        description="Return details of the currently logged-in user (email, organization, role).",
        responses={200: UserDetailSerializer},
    )
    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)


@extend_schema(tags=["Team Management"])
class CreateTeamMemberView(generics.CreateAPIView):
    """
    POST /api/auth/team/
    Allows an authenticated user (Owner) to add a new employee to their Organization.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer

    @extend_schema(
        summary="Add Team Member", description="Create a new user linked to your Organization. Only Owners can do this."
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["API Keys"])
@extend_schema_view(
    list=extend_schema(summary="List API Keys", description="Get all active API keys (masked)"),
    create=extend_schema(
        summary="Generate API Key", description="Create a new key. WARNING: Full key is shown only once!"
    ),
    destroy=extend_schema(summary="Revoke API Key"),
)
class OrganizationApiKeyViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationApiKeySerializer

    def get_queryset(self):
        if getattr(self.request.user, "organization", None):
            return OrganizationApiKey.objects.filter(organization=self.request.user.organization)
        return OrganizationApiKey.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
