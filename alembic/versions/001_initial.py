"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Competitions table
    op.create_table(
        'competitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('location', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_competitions_id', 'competitions', ['id'])

    # Athletes table
    op.create_table(
        'athletes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('gender', sa.String(20), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('division', sa.String(50), nullable=False),
        sa.Column('box', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(30), nullable=True),
        sa.Column('bib_number', sa.String(20), nullable=False),
        sa.Column('competition_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bib_number', 'competition_id', name='uq_athlete_bib_competition'),
    )
    op.create_index('ix_athletes_id', 'athletes', ['id'])
    op.create_index('ix_athlete_competition_division', 'athletes', ['competition_id', 'division'])

    # WODs table
    op.create_table(
        'wods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('wod_type', sa.String(20), nullable=False),
        sa.Column('time_cap', sa.Integer(), nullable=True),
        sa.Column('order_in_competition', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('competition_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_wods_id', 'wods', ['id'])
    op.create_index('ix_wod_competition_order', 'wods', ['competition_id', 'order_in_competition'])

    # WOD Standards table
    op.create_table(
        'wod_standards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wod_id', sa.Integer(), nullable=False),
        sa.Column('division', sa.String(50), nullable=False),
        sa.Column('rx_weight_kg', sa.Float(), nullable=True),
        sa.Column('description_override', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['wod_id'], ['wods.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wod_id', 'division', name='uq_wod_standard_division'),
    )
    op.create_index('ix_wod_standards_id', 'wod_standards', ['id'])

    # Scores table
    op.create_table(
        'scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('wod_id', sa.Integer(), nullable=False),
        sa.Column('raw_result', sa.Float(), nullable=True),
        sa.Column('result_type', sa.String(20), nullable=False, server_default='RX'),
        sa.Column('tiebreak', sa.Float(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('points', sa.Float(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('judge_id', sa.Integer(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.ForeignKeyConstraint(['wod_id'], ['wods.id']),
        sa.ForeignKeyConstraint(['judge_id'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('athlete_id', 'wod_id', name='uq_score_athlete_wod'),
    )
    op.create_index('ix_scores_id', 'scores', ['id'])
    op.create_index('ix_score_wod_rank', 'scores', ['wod_id', 'rank'])

    # Score Audit Logs table
    op.create_table(
        'score_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('score_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['score_id'], ['scores.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_score_audit_logs_id', 'score_audit_logs', ['id'])
    op.create_index('ix_audit_score_timestamp', 'score_audit_logs', ['score_id', 'timestamp'])
    op.create_index('ix_audit_user_timestamp', 'score_audit_logs', ['user_id', 'timestamp'])


def downgrade() -> None:
    op.drop_table('score_audit_logs')
    op.drop_table('scores')
    op.drop_table('wod_standards')
    op.drop_table('wods')
    op.drop_table('athletes')
    op.drop_table('competitions')
    op.drop_table('users')
