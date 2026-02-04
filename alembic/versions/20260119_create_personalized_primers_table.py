"""create personalized primers table

Revision ID: personalized_primers_001
Revises: baseline_primers_001
Create Date: 2026-01-19 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'personalized_primers_001'
down_revision = 'baseline_primers_001'
branch_labels = None
depends_on = None


def upgrade():
    # Create personalized_primers table
    op.create_table(
        'personalized_primers',
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('lesson_id', sa.BigInteger(), nullable=False),
        sa.Column('personalized_bullets', JSONB, nullable=False),
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('inputs_hash', sa.Text(), nullable=False),
        sa.Column('lesson_version', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('memory_version', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('ttl_expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('stale', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'lesson_id'),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE')
    )

    # Create indexes for performance
    op.create_index('idx_personalized_primers_ttl', 'personalized_primers', ['ttl_expires_at'])
    op.create_index('idx_personalized_primers_user_id', 'personalized_primers', ['user_id'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_personalized_primers_user_id', table_name='personalized_primers')
    op.drop_index('idx_personalized_primers_ttl', table_name='personalized_primers')

    # Drop table
    op.drop_table('personalized_primers')
