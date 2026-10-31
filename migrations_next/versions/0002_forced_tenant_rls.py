"""Enable forced PostgreSQL row-level tenant isolation.

Revision ID: ng_0002
Revises: ng_0001
"""
from alembic import op

from app.db.nextgen.rls import (
    disable_tenant_rls_statements,
    enable_tenant_rls_statements,
)

revision = "ng_0002"
down_revision = "ng_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in enable_tenant_rls_statements():
        op.execute(statement)


def downgrade() -> None:
    for statement in disable_tenant_rls_statements():
        op.execute(statement)
