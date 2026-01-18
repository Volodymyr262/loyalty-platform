"""
URL configuration for the users application API.
"""

from django.urls import include, path
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from users.views import CreateTeamMemberView, OrganizationApiKeyViewSet, RegisterTenantView, UserProfileView

router = DefaultRouter()
router.register(r"api-keys", OrganizationApiKeyViewSet, basename="organization-api-keys")

urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterTenantView.as_view(), name="auth_register"),
    path("login/", TokenObtainPairView.as_view(permission_classes=[AllowAny]), name="auth_login"),
    path("refresh/", TokenRefreshView.as_view(permission_classes=[AllowAny]), name="auth_refresh"),
    path("me/", UserProfileView.as_view(), name="auth_me"),
    path("team/", CreateTeamMemberView.as_view(), name="auth_team_create"),
]
