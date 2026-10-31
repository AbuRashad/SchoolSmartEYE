"""%(message)s

Revision ID: %(rev)s
Revises: %(down_revision)s
Create Date: %(create_date)s
"""
from alembic import op
import sqlalchemy as sa
{% if false else ""}

revision = %(rev)r
down_revision = %(down_revision)r
branch_labels = %(branch_labels)r
depends_on = %(depends_on)r


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
