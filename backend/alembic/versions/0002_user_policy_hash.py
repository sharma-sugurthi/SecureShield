"""per-user policy hash uniqueness

Revision ID: 0002_user_policy_hash
Revises: 0001_initial
Create Date: 2026-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_user_policy_hash'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove any legacy global raw_text_hash uniqueness/indexing
    try:
        op.drop_index('ix_policies_raw_text_hash', table_name='policies')
    except Exception:
        pass
    try:
        op.drop_index('idx_policies_hash', table_name='policies')
    except Exception:
        pass

    op.create_index('idx_policies_hash', 'policies', ['raw_text_hash'])
    op.create_unique_constraint('uq_policy_user_hash', 'policies', ['user_id', 'raw_text_hash'])


def downgrade() -> None:
    op.drop_constraint('uq_policy_user_hash', 'policies', type_='unique')
    try:
        op.drop_index('idx_policies_hash', table_name='policies')
    except Exception:
        pass
    op.create_index('idx_policies_hash', 'policies', ['raw_text_hash'])
