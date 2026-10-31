from app.db.nextgen.rls import (
    TENANT_TABLES,
    disable_tenant_rls_statements,
    enable_tenant_rls_statements,
)


def test_rls_covers_every_declared_tenant_table_once():
    statements = enable_tenant_rls_statements()
    sql = "\n".join(statements)
    for table in TENANT_TABLES:
        assert f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY' in sql
        assert f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY' in sql
        assert f'CREATE POLICY "tenant_isolation" ON "{table}"' in sql
    assert len(TENANT_TABLES) == len(set(TENANT_TABLES))


def test_rls_policies_fail_closed_without_transaction_context():
    sql = "\n".join(enable_tenant_rls_statements())
    assert "current_setting('app.organization_id', true)" in sql
    assert "current_setting('app.school_id', true)" in sql
    assert "WITH CHECK" in sql
    assert "ministry_reader" in sql


def test_global_identity_tables_are_scoped_too():
    sql = "\n".join(enable_tenant_rls_statements())
    assert 'ON "ng_organizations"' in sql
    assert 'ON "ng_users"' in sql
    assert "m.status = 'active'" in sql


def test_downgrade_removes_only_the_named_policy_and_disables_rls():
    sql = "\n".join(disable_tenant_rls_statements())
    assert 'DROP POLICY IF EXISTS "tenant_isolation"' in sql
    assert "DISABLE ROW LEVEL SECURITY" in sql


def test_user_identity_policy_is_read_only_for_application_role():
    sql = "\\n".join(enable_tenant_rls_statements())
    user_policy = next(line for line in sql.splitlines() if 'ON "ng_users" FOR SELECT' in line)
    assert "FOR SELECT" in user_policy
    assert 'CREATE POLICY "tenant_isolation" ON "ng_users" ' in sql
    assert 'CREATE POLICY "tenant_isolation" ON "ng_users" FOR ALL' not in sql
