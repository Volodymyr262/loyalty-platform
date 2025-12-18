"""
Authentication Views.
"""

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import TeamMemberSerializer, TenantRegistrationSerializer, UserDetailSerializer


class RegisterTenantView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Public endpoint to register a new tenant.
    """

    permission_classes = [AllowAny]
    serializer_class = TenantRegistrationSerializer


class UserProfileView(APIView):
    """
    GET /api/auth/me/
    Returns details about the currently logged-in user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class CreateTeamMemberView(generics.CreateAPIView):
    """
    POST /api/auth/team/
    Allows an authenticated user (Owner) to add a new employee to their Organization.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer
