"""
Alter user_progress.user_id to VARCHAR(128) and add index

Revision ID: userid_to_string
Revises: 
Create Date: 2025-10-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'userid_to_string'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1) Alter column type from BIGINT to VARCHAR(128) using USING cast
    op.alter_column(
        'user_progress',
        'user_id',
        type_=sa.String(length=128),
        existing_type=sa.BigInteger(),
        postgresql_using='user_id::text',
        existing_nullable=True,
    )

    # 2) Create index on user_id if not exists
    op.create_index('ix_user_progress_user_id', 'user_progress', ['user_id'], unique=False)


def downgrade():
    # Drop index
    op.drop_index('ix_user_progress_user_id', table_name='user_progress')

    # Convert back to BIGINT (data loss possible if non-numeric)
    op.alter_column(
        'user_progress',
        'user_id',
        type_=sa.BigInteger(),
        existing_type=sa.String(length=128),
        postgresql_using="NULLIF(user_id, '')::bigint",
        existing_nullable=True,
    )
