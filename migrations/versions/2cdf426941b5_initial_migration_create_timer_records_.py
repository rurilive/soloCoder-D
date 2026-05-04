"""initial migration: create timer_records table

Revision ID: 2cdf426941b5
Revises: 
Create Date: 2026-05-04 15:36:38.729629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = '2cdf426941b5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'timer_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mode', sa.Enum('WORK', 'SHORT_BREAK', 'LONG_BREAK', 'CUSTOM', name='timermode'), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timer_records_id'), 'timer_records', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_timer_records_id'), table_name='timer_records')
    op.drop_table('timer_records')
