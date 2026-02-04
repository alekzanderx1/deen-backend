"""add baseline primers to lessons

Revision ID: baseline_primers_001
Revises: a12c6d22b9d9
Create Date: 2026-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'baseline_primers_001'
down_revision = 'a12c6d22b9d9'
branch_labels = None
depends_on = None


def upgrade():
    # Add baseline_primer_bullets column (JSONB to store array of bullet strings)
    op.add_column('lessons', sa.Column('baseline_primer_bullets', JSONB, nullable=True))

    # Add baseline_primer_glossary column (JSONB to store key-value pairs)
    op.add_column('lessons', sa.Column('baseline_primer_glossary', JSONB, nullable=True))

    # Add baseline_primer_updated_at column (timestamp to track when baseline was last updated)
    op.add_column('lessons', sa.Column('baseline_primer_updated_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade():
    # Remove columns in reverse order
    op.drop_column('lessons', 'baseline_primer_updated_at')
    op.drop_column('lessons', 'baseline_primer_glossary')
    op.drop_column('lessons', 'baseline_primer_bullets')
