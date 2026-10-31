import pytest

from app.db.nextgen.authorization import (
    AuthorizationError,
    TenantContext,
    authorize,
)


def test_teacher_can_read_only_within_assigned_school():
    context = TenantContext("u1", "org1", "school1", "teacher")
    authorize(context, "student:read", organization_id="org1", school_id="school1")
    with pytest.raises(AuthorizationError, match="School scope mismatch"):
        authorize(context, "student:read", organization_id="org1", school_id="school2")


def test_cross_organization_access_is_denied():
    context = TenantContext("u1", "org1", "school1", "school_admin")
    with pytest.raises(AuthorizationError, match="Organization scope mismatch"):
        authorize(context, "student:read", organization_id="org2", school_id="school1")


def test_inactive_membership_is_denied():
    context = TenantContext("u1", "org1", "school1", "principal", "suspended")
    with pytest.raises(AuthorizationError, match="not active"):
        authorize(context, "analytics:read", organization_id="org1", school_id="school1")


def test_unknown_role_and_unlisted_permission_fail_closed():
    context = TenantContext("u1", "org1", "school1", "superuser")
    with pytest.raises(AuthorizationError, match="Permission denied"):
        authorize(context, "database:drop", organization_id="org1", school_id="school1")


def test_teacher_cannot_manage_users():
    context = TenantContext("u1", "org1", "school1", "teacher")
    with pytest.raises(AuthorizationError, match="Permission denied"):
        authorize(context, "user:manage", organization_id="org1", school_id="school1")


def test_ministry_reader_is_organization_wide_but_read_only():
    context = TenantContext("u1", "org1", None, "ministry_reader")
    authorize(context, "analytics:read", organization_id="org1", school_id="school9")
    with pytest.raises(AuthorizationError, match="Permission denied"):
        authorize(context, "student:write", organization_id="org1", school_id="school9")


def test_school_role_cannot_use_organization_wide_scope():
    context = TenantContext("u1", "org1", None, "principal")
    with pytest.raises(AuthorizationError, match="School-scoped"):
        authorize(context, "analytics:read", organization_id="org1", school_id="school1")
