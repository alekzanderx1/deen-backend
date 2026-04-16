"""Initial schema — base tables that existed before alembic was introduced.

Revision ID: initial_schema_001
Revises:
Create Date: 2026-04-06

Creates the five tables that pre-dated the alembic migration chain.
Subsequent migrations alter these tables and create additional ones.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision = 'initial_schema_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # users
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('email', sa.Text(), unique=True),
        sa.Column('password_hash', sa.Text()),
        sa.Column('display_name', sa.Text()),
        sa.Column('avatar_url', sa.Text()),
        sa.Column('role', sa.Text()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # hikmah_trees
    op.create_table(
        'hikmah_trees',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.Text()),
        sa.Column('summary', sa.Text()),
        sa.Column('tags', ARRAY(sa.Text())),
        sa.Column('skill_level', sa.Integer()),
        sa.Column('meta', JSONB()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # lessons — without the 3 baseline_primer_* columns added by migration baseline_primers_001
    op.create_table(
        'lessons',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('slug', sa.Text(), unique=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('tags', ARRAY(sa.Text())),
        sa.Column('status', sa.Text()),
        sa.Column('language_code', sa.Text()),
        sa.Column('author_user_id', sa.BigInteger()),
        sa.Column('estimated_minutes', sa.Integer()),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('hikmah_tree_id', sa.BigInteger()),
        sa.Column('order_position', sa.Integer()),
    )

    # lesson_content
    op.create_table(
        'lesson_content',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.BigInteger()),
        sa.Column('order_position', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text()),
        sa.Column('content_type', sa.Text()),
        sa.Column('content_body', sa.Text()),
        sa.Column('content_json', JSONB()),
        sa.Column('media_urls', JSONB()),
        sa.Column('est_minutes', sa.Integer()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # user_progress — original schema before userid_to_string and a12c6d22b9d9 migrations:
    #   user_id was BigInteger nullable (migration 1 changes to VARCHAR(128))
    #   hikmah_tree_id was NOT NULL (migration 2 makes nullable)
    op.create_table(
        'user_progress',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('hikmah_tree_id', sa.BigInteger(), nullable=False),
        sa.Column('lesson_id', sa.BigInteger()),
        sa.Column('content_id', sa.BigInteger()),
        sa.Column('is_completed', sa.Boolean(), server_default='false'),
        sa.Column('percent_complete', sa.Numeric(5, 2)),
        sa.Column('last_position', sa.Integer()),
        sa.Column('notes', sa.Text()),
        sa.Column('meta', JSONB()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('user_progress')
    op.drop_table('lesson_content')
    op.drop_table('lessons')
    op.drop_table('hikmah_trees')
    op.drop_table('users')
