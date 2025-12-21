"""
URL configuration for the users application API.
"""

from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import CreateTeamMemberView, RegisterTenantView, UserProfileView

urlpatterns = [
    # Custom Registration
    path("register/", RegisterTenantView.as_view(), name="auth_register"),
    # Standard JWT Login (returns access + refresh tokens)
    path("login/", TokenObtainPairView.as_view(permission_classes=[AllowAny]), name="auth_login"),
    # Standard JWT Refresh (returns new access token)
    path("refresh/", TokenRefreshView.as_view(permission_classes=[AllowAny]), name="auth_refresh"),
    # User Profile
    path("me/", UserProfileView.as_view(), name="auth_me"),
    # Create new employee user  for organization
    path("team/", CreateTeamMemberView.as_view(), name="auth_team_create"),
]
