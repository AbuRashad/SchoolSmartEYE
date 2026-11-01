"""Apply trusted tenant context to a PostgreSQL transaction.

The caller must derive TenantContext from the authenticated principal and an
active database membership. Never build it from request-supplied tenant/role
fields. PostgreSQL SET LOCAL semantics ensure values disappear at transaction
end and do not leak through pooled connections.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.nextgen.authorization import AuthorizationError, TenantContext

_SET_LOCAL = text(
    "SELECT "
    "set_config('app.organization_id', :organization_id, true), "
    "set_config('app.school_id', :school_id, true), "
    "set_config('app.role', :role, true), "
    "set_config('app.user_id', :user_id, true)"
)


def apply_tenant_scope(session: Session, context: TenantContext) -> None:
    """Set transaction-local PostgreSQL variables consumed by RLS policies.

    Must be called after a transaction has begun and before tenant queries.
    This function does not commit, begin, or end the caller's transaction.
    """
    if not context.user_id or not context.organization_id:
        raise AuthorizationError("Authenticated tenant context is required")
    if context.membership_status != "active":
        raise AuthorizationError("Membership is not active")
    if context.role not in {
        "ministry_reader", "school_admin", "principal", "teacher", "reviewer"
    }:
        raise AuthorizationError("Unknown role")

    if context.role == "ministry_reader":
        if context.school_id is not None:
            raise AuthorizationError("Ministry reader must use organization-wide scope")
    elif not context.school_id:
        raise AuthorizationError("School-scoped membership is required")

    session.execute(
        _SET_LOCAL,
        {
            "organization_id": context.organization_id,
            "school_id": context.school_id or "",
            "role": context.role,
            "user_id": context.user_id,
        },
    )
