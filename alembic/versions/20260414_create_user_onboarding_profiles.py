"""create user onboarding profiles table

Revision ID: onboarding_profiles_001
Revises: embeddings_002
Create Date: 2026-04-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = 'onboarding_profiles_001'
down_revision = 'embeddings_002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_onboarding_profiles',
        sa.Column('user_id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('tradition', sa.Text(), nullable=False),
        sa.Column('goals', ARRAY(sa.Text()), nullable=False),
        sa.Column('knowledge_level', sa.Text(), nullable=False),
        sa.Column('topics', ARRAY(sa.Text()), nullable=False),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_user_onboarding_profiles_user_id', 'user_onboarding_profiles', ['user_id'])


def downgrade():
    op.drop_index('idx_user_onboarding_profiles_user_id', table_name='user_onboarding_profiles')
    op.drop_table('user_onboarding_profiles')
