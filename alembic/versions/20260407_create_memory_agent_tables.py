"""create memory agent tables

Revision ID: memory_agent_001
Revises: chat_history_001
Create Date: 2026-04-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'memory_agent_001'
down_revision = 'chat_history_001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_memory_profiles',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('preferred_language', sa.String(), server_default=sa.text("'english'")),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('learning_notes', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('interest_notes', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('knowledge_notes', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('behavior_notes', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('preference_notes', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('total_interactions', sa.Integer(), server_default='0'),
        sa.Column('last_significant_update', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('memory_version', sa.Integer(), server_default='1'),
        sa.UniqueConstraint('user_id', name='uq_user_memory_profiles_user_id'),
    )
    op.create_index('idx_user_memory_profiles_user_id', 'user_memory_profiles', ['user_id'])

    op.create_table(
        'memory_events',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_memory_profile_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('trigger_context', sa.JSON(), nullable=True),
        sa.Column('notes_added', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('memory_updates', sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('processing_reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('processing_status', sa.String(), server_default=sa.text("'pending'")),
        sa.ForeignKeyConstraint(['user_memory_profile_id'], ['user_memory_profiles.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_memory_events_profile_id', 'memory_events', ['user_memory_profile_id'])
    op.create_index('idx_memory_events_status', 'memory_events', ['processing_status'])

    op.create_table(
        'memory_consolidations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_memory_profile_id', sa.String(), nullable=False),
        sa.Column('consolidation_type', sa.String(), nullable=False),
        sa.Column('notes_before_count', sa.Integer(), nullable=True),
        sa.Column('notes_after_count', sa.Integer(), nullable=True),
        sa.Column('consolidated_notes', sa.JSON(), nullable=True),
        sa.Column('removed_notes', sa.JSON(), nullable=True),
        sa.Column('new_summary_notes', sa.JSON(), nullable=True),
        sa.Column('consolidation_reasoning', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_memory_profile_id'], ['user_memory_profiles.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_memory_consolidations_profile_id', 'memory_consolidations', ['user_memory_profile_id'])


def downgrade():
    op.drop_index('idx_memory_consolidations_profile_id', table_name='memory_consolidations')
    op.drop_table('memory_consolidations')

    op.drop_index('idx_memory_events_status', table_name='memory_events')
    op.drop_index('idx_memory_events_profile_id', table_name='memory_events')
    op.drop_table('memory_events')

    op.drop_index('idx_user_memory_profiles_user_id', table_name='user_memory_profiles')
    op.drop_table('user_memory_profiles')
