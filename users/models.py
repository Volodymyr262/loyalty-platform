"""
Models for the users application (Auth and Organization/Tenant)
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model.
    Linked to an Organization to know which Tenant data to access.
    """

    organization = models.ForeignKey(
        "users.Organization", on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )

    def __str__(self):
        return f"{self.username} ({self.organization.name if self.organization else 'No Org'})"


class Organization(models.Model):
    """
    Represents a Tenant (Business Client) in the system.
    """

    # Use UUID for primary key to avoid enumeration attacks
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)

    # The API Key used for Server-to-Server authentication via X-Tenant-API-Key header
    api_key = models.CharField(max_length=64, unique=True, db_index=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
