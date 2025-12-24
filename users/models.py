"""
Models for the users application (Auth and Organization/Tenant)
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from users.managers import CustomUserManager  # <--- Імпортуємо наш менеджер


class Organization(models.Model):
    """
    Represents a Tenant (Business Client) in the system.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OrganizationApiKey(models.Model):
    """
    Separate model for managing API keys.
    Allows key rotation and multiple keys per organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=50, help_text="e.g. 'Website' or 'POS Terminal 1'")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.organization.name} - {self.name}"


class User(AbstractUser):
    """
    Custom User model supporting Email login.
    """

    username = None
    email = models.EmailField("email address", unique=True)

    organization = models.ForeignKey(
        "users.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
