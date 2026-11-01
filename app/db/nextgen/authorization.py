"""Fail-closed authorization primitives for next-generation tenant access.

This module is framework-agnostic. API dependencies should build TenantContext
from the authenticated principal and an active ng_memberships row; never accept
tenant identifiers or roles directly from an untrusted request body.
"""
from __future__ import annotations

from dataclasses import dataclass


class AuthorizationError(PermissionError):
    """Raised when a principal is not authorized for an operation or tenant."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    user_id: str
    organization_id: str
    school_id: str | None
    role: str
    membership_status: str = "active"


# Explicit allow-list: unknown roles and permissions are denied by default.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ministry_reader": frozenset({
        "analytics:read", "school:read", "incident:read", "audit:read",
    }),
    "school_admin": frozenset({
        "school:read", "school:write", "user:manage", "student:read",
        "student:write", "attendance:read", "attendance:write",
        "camera:read", "camera:write", "incident:read", "incident:manage",
        "review:read", "review:write", "analytics:read", "consent:read",
        "consent:manage", "audit:read",
    }),
    "principal": frozenset({
        "school:read", "student:read", "attendance:read", "attendance:write",
        "camera:read", "incident:read", "incident:manage", "review:read",
        "review:write", "analytics:read", "consent:read", "audit:read",
    }),
    "teacher": frozenset({
        "student:read", "attendance:read", "attendance:write",
        "incident:read", "analytics:read",
    }),
    "reviewer": frozenset({
        "incident:read", "review:read", "review:write", "audit:read",
    }),
}


def authorize(
    context: TenantContext,
    permission: str,
    *,
    organization_id: str,
    school_id: str | None,
) -> None:
    """Validate active membership, tenant boundary, school scope and permission.

    A ministry_reader may have organization-wide scope (school_id=None).
    Every other role must be bound to exactly one school. A school-scoped
    membership cannot access a different school, even inside its organization.
    """
    if not context.user_id or not context.organization_id:
        raise AuthorizationError("Authenticated tenant context is required")
    if context.membership_status != "active":
        raise AuthorizationError("Membership is not active")
    if context.organization_id != organization_id:
        raise AuthorizationError("Organization scope mismatch")

    if context.role == "ministry_reader":
        if context.school_id is not None:
            raise AuthorizationError("Ministry reader must use organization-wide scope")
    else:
        if not context.school_id:
            raise AuthorizationError("School-scoped membership is required")
        if school_id is None or context.school_id != school_id:
            raise AuthorizationError("School scope mismatch")

    allowed = ROLE_PERMISSIONS.get(context.role, frozenset())
    if permission not in allowed:
        raise AuthorizationError("Permission denied")
