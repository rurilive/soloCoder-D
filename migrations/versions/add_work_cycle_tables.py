"""add work cycle tables

Revision ID: add_work_cycle_tables
Revises: 2cdf426941b5
Create Date: 2026-05-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = 'add_work_cycle_tables'
down_revision: Union[str, Sequence[str], None] = '2cdf426941b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'work_cycles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('total_pomodoros', sa.Integer(), nullable=False),
        sa.Column('completed_pomodoros', sa.Integer(), nullable=False),
        sa.Column('work_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('short_break_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('long_break_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'CANCELLED', name='cyclestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_cycles_id'), 'work_cycles', ['id'], unique=False)

    op.create_table(
        'cycle_segments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('work_cycle_id', sa.Integer(), nullable=False),
        sa.Column('segment_order', sa.Integer(), nullable=False),
        sa.Column('segment_type', sa.Enum('WORK', 'SHORT_BREAK', 'LONG_BREAK', 'CUSTOM', name='timermode'), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['work_cycle_id'], ['work_cycles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cycle_segments_id'), 'cycle_segments', ['id'], unique=False)

    op.add_column('timer_records', sa.Column('cycle_segment_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_timer_records_cycle_segment_id',
        'timer_records',
        'cycle_segments',
        ['cycle_segment_id'],
        ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_timer_records_cycle_segment_id', 'timer_records', type_='foreignkey')
    op.drop_column('timer_records', 'cycle_segment_id')
    
    op.drop_index(op.f('ix_cycle_segments_id'), table_name='cycle_segments')
    op.drop_table('cycle_segments')
    
    op.drop_index(op.f('ix_work_cycles_id'), table_name='work_cycles')
    op.drop_table('work_cycles')
    
    op.execute('DROP TYPE IF EXISTS cyclestatus')
