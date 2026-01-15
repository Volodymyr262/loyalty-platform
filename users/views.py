"""
Authentication Views.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import TeamMemberSerializer, TenantRegistrationSerializer, UserDetailSerializer


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
