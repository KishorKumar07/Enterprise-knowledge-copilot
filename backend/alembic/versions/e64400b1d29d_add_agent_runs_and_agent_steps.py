"""add agent_runs and agent_steps

Revision ID: e64400b1d29d
Revises: d6841b6be091
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e64400b1d29d'
down_revision: Union[str, None] = 'd6841b6be091'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('agent_runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('conversation_id', sa.UUID(), nullable=False),
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('query', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_conversation_id'), 'agent_runs', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_agent_runs_organization_id'), 'agent_runs', ['organization_id'], unique=False)

    op.create_table('agent_steps',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('node_name', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_steps_run_id'), 'agent_steps', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agent_steps_run_id'), table_name='agent_steps')
    op.drop_table('agent_steps')
    op.drop_index(op.f('ix_agent_runs_organization_id'), table_name='agent_runs')
    op.drop_index(op.f('ix_agent_runs_conversation_id'), table_name='agent_runs')
    op.drop_table('agent_runs')
