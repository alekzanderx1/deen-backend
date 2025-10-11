"""
Revision ID: a12c6d22b9d9
Revises: userid_to_string
Create Date: 2025-10-07 22:26:19.001539
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a12c6d22b9d9'
down_revision = 'userid_to_string'
branch_labels = None
depends_on = None


def upgrade():
    # Make hikmah_tree_id nullable
    op.alter_column('user_progress', 'hikmah_tree_id',
                    existing_type=sa.BigInteger(),
                    nullable=True)


def downgrade():
    # Revert: make hikmah_tree_id NOT NULL (may fail if NULL values exist)
    op.alter_column('user_progress', 'hikmah_tree_id',
                    existing_type=sa.BigInteger(),
                    nullable=False)
