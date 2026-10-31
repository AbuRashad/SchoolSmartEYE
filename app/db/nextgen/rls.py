"""PostgreSQL row-level security policy definitions for tenant-owned tables."""
from __future__ import annotations

# Explicit allow-list: every table here has organization_id and school_id.
TENANT_TABLES = (
    "ng_campuses", "ng_memberships", "ng_guardians", "ng_students",
    "ng_student_guardians", "ng_classes", "ng_enrollments",
    "ng_attendance_events", "ng_buildings", "ng_zones", "ng_cameras",
    "ng_edge_devices", "ng_camera_telemetry", "ng_ai_events", "ng_incidents",
    "ng_human_reviews", "ng_metric_observations", "ng_consent_records",
    "ng_audit_events",
)

TENANT_POLICY = """
organization_id = NULLIF(current_setting('app.organization_id', true), '')
AND (
    current_setting('app.role', true) = 'ministry_reader'
    OR school_id = NULLIF(current_setting('app.school_id', true), '')
)
"""


def enable_tenant_rls_statements() -> tuple[str, ...]:
    """Return DDL for the allow-listed tenant tables only."""
    statements: list[str] = []
    for table in TENANT_TABLES:
        statements.extend((
            f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY',
            f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY',
            f'CREATE POLICY "tenant_isolation" ON "{table}" '
            f"USING ({TENANT_POLICY}) WITH CHECK ({TENANT_POLICY})",
        ))
    statements.extend((
        'ALTER TABLE "ng_organizations" ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE "ng_organizations" FORCE ROW LEVEL SECURITY',
        'CREATE POLICY "tenant_isolation" ON "ng_organizations" '
        "USING (id = NULLIF(current_setting('app.organization_id', true), '')) "
        "WITH CHECK (id = NULLIF(current_setting('app.organization_id', true), ''))",
        'ALTER TABLE "ng_users" ENABLE ROW LEVEL SECURITY',
        'ALTER TABLE "ng_users" FORCE ROW LEVEL SECURITY',
        # User provisioning is intentionally outside the application RLS policy.
        # An audited privileged onboarding path must create users/memberships.
        'CREATE POLICY "tenant_isolation" ON "ng_users" FOR SELECT '
        "USING (EXISTS (SELECT 1 FROM ng_memberships m "
        "WHERE m.user_id = ng_users.id "
        "AND m.organization_id = NULLIF(current_setting('app.organization_id', true), '') "
        "AND (current_setting('app.role', true) = 'ministry_reader' "
        "OR m.school_id = NULLIF(current_setting('app.school_id', true), '')) "
        "AND m.status = 'active'))",
    ))
    return tuple(statements)


def disable_tenant_rls_statements() -> tuple[str, ...]:
    """Remove this migration's policies and disable RLS during explicit downgrade."""
    tables = (*TENANT_TABLES, "ng_organizations", "ng_users")
    statements: list[str] = []
    for table in tables:
        statements.extend((
            f'DROP POLICY IF EXISTS "tenant_isolation" ON "{table}"',
            f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY',
            f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY',
        ))
    return tuple(statements)
