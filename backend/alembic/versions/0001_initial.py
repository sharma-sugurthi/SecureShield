"""initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2026-06-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('insurer', sa.String(), nullable=False),
        sa.Column('plan_name', sa.String(), nullable=False),
        sa.Column('sum_insured', sa.Float(), nullable=False),
        sa.Column('policy_type', sa.String(), nullable=True, server_default='individual'),
        sa.Column('rules_json', sa.Text(), nullable=False),
        sa.Column('raw_text_hash', sa.String(), nullable=True),
        sa.Column('is_reviewed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_policies_hash', 'policies', ['raw_text_hash'])

    op.create_table(
        'eligibility_checks',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('case_json', sa.Text(), nullable=False),
        sa.Column('verdict_json', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('eligibility_checks')
    op.drop_index('idx_policies_hash', table_name='policies')
    op.drop_table('policies')
