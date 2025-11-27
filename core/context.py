"""
Context management utilities for tenant isolation handling.
"""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

# Context variable to hold the ID of the current active organization
# Using contextvars ensures thread-safety and async compatibility
_current_organization_id: ContextVar[Optional[UUID]] = ContextVar("current_organization_id", default=None)


def set_current_organization_id(organization_id: UUID):
    """
    Sets the organization UUID for the current execution context.
    """
    _current_organization_id.set(organization_id)


def get_current_organization_id() -> Optional[UUID]:
    """
    Retrieves the organization UUID from the current execution context.
    Returns None if no context is active.
    """
    return _current_organization_id.get()


def reset_current_organization_id():
    """
    Resets the context variable to None.
    """
    _current_organization_id.set(None)
