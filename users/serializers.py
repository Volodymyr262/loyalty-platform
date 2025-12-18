"""
Serializers for User authentication and profile management.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Organization

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serializer to display Organization details nested inside User profile.
    """

    class Meta:
        model = Organization
        fields = ["id", "name", "api_key"]
        read_only_fields = ["id", "api_key"]


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing the current user's profile (/me/).
    """

    organization = OrganizationSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "organization"]


class TenantRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new Tenant (User + Organization).
    """

    organization_name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "password", "organization_name"]

    def create(self, validated_data):
        """
        Custom create method to handle atomic creation of Organization and User.
        """
        org_name = validated_data.pop("organization_name")
        email = validated_data.get("email")
        password = validated_data.get("password")

        with transaction.atomic():
            # 1. Create Organization
            organization = Organization.objects.create(name=org_name)

            # 2. Create User linked to this Organization
            user = User.objects.create_user(email=email, password=password, organization=organization)

        return user

    def to_representation(self, instance):
        """
        Customize response to include JWT tokens immediately after registration.
        """
        data = super().to_representation(instance)

        # Generate tokens manually
        refresh = RefreshToken.for_user(instance)

        data["organization"] = OrganizationSerializer(instance.organization).data
        data["access"] = str(refresh.access_token)
        data["refresh"] = str(refresh)

        return data


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for adding new users to an EXISTING organization.
    Only accessible by authenticated admins/owners.
    """

    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        """
        Create a user and link them to the requestor's organization.
        """
        request = self.context.get("request")
        if request and request.user and request.user.organization:
            organization = request.user.organization
        else:
            raise serializers.ValidationError("You must belong to an organization to add members.")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            organization=organization,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        return user
