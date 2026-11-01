from app.db.nextgen.authorization import AuthorizationError, TenantContext
from app.db.nextgen.scope import apply_tenant_scope


class RecordingSession:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((statement, params))


def test_scope_sets_transaction_local_values_from_trusted_context():
    session = RecordingSession()
    context = TenantContext("user-1", "org-1", "school-1", "teacher")

    apply_tenant_scope(session, context)

    assert len(session.calls) == 1
    _, params = session.calls[0]
    assert params == {
        "organization_id": "org-1",
        "school_id": "school-1",
        "role": "teacher",
        "user_id": "user-1",
    }


def test_ministry_scope_uses_empty_school_id_for_org_wide_access():
    session = RecordingSession()
    apply_tenant_scope(
        session, TenantContext("user-1", "org-1", None, "ministry_reader")
    )
    assert session.calls[0][1]["school_id"] == ""


def test_scope_rejects_inactive_membership_before_database_call():
    session = RecordingSession()
    context = TenantContext("user-1", "org-1", "school-1", "teacher", "suspended")
    try:
        apply_tenant_scope(session, context)
    except AuthorizationError as exc:
        assert "not active" in str(exc)
    else:
        raise AssertionError("Expected inactive membership to be rejected")
    assert session.calls == []


def test_scope_rejects_school_role_without_school():
    session = RecordingSession()
    context = TenantContext("user-1", "org-1", None, "principal")
    try:
        apply_tenant_scope(session, context)
    except AuthorizationError as exc:
        assert "School-scoped" in str(exc)
    else:
        raise AssertionError("Expected missing school scope to be rejected")
    assert session.calls == []
