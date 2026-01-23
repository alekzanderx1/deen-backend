"""create embedding tables for notes and lesson chunks

Revision ID: embeddings_001
Revises: personalized_primers_001
Create Date: 2026-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'embeddings_001'
down_revision = 'personalized_primers_001'
branch_labels = None
depends_on = None

# Embedding dimensions for OpenAI text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536


def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create note_embeddings table
    op.create_table(
        'note_embeddings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.String(length=128), nullable=False),
        sa.Column('note_id', sa.String(length=128), nullable=False),
        sa.Column('note_type', sa.String(length=50), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes for note_embeddings
    op.create_index('idx_note_embeddings_user_id', 'note_embeddings', ['user_id'])
    op.create_index('idx_note_embeddings_note_type', 'note_embeddings', ['note_type'])
    op.create_index('idx_note_embeddings_user_note', 'note_embeddings', ['user_id', 'note_id'], unique=True)

    # Create HNSW index for vector similarity search (cosine distance)
    op.execute("""
        CREATE INDEX idx_note_embeddings_vector
        ON note_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Create lesson_chunk_embeddings table (multiple chunks per lesson)
    op.create_table(
        'lesson_chunk_embeddings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.BigInteger(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),  # Order of chunk within lesson
        sa.Column('chunk_text', sa.Text(), nullable=False),  # The actual chunk content
        sa.Column('content_hash', sa.String(length=64), nullable=False),  # Hash of full lesson content
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
    )

    # Create indexes for lesson_chunk_embeddings
    op.create_index('idx_lesson_chunk_lesson_id', 'lesson_chunk_embeddings', ['lesson_id'])
    op.create_index('idx_lesson_chunk_unique', 'lesson_chunk_embeddings', ['lesson_id', 'chunk_index'], unique=True)

    # Create HNSW index for vector similarity search on lesson chunks
    op.execute("""
        CREATE INDEX idx_lesson_chunk_embeddings_vector
        ON lesson_chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    # Drop lesson_chunk_embeddings
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_embeddings_vector')
    op.drop_index('idx_lesson_chunk_unique', table_name='lesson_chunk_embeddings')
    op.drop_index('idx_lesson_chunk_lesson_id', table_name='lesson_chunk_embeddings')
    op.drop_table('lesson_chunk_embeddings')

    # Drop note_embeddings
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_vector')
    op.drop_index('idx_note_embeddings_user_note', table_name='note_embeddings')
    op.drop_index('idx_note_embeddings_note_type', table_name='note_embeddings')
    op.drop_index('idx_note_embeddings_user_id', table_name='note_embeddings')
    op.drop_table('note_embeddings')

    # Note: We don't drop the vector extension as other tables might use it
