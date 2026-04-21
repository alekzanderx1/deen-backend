"""resize embedding vector columns from 1536 to 768 (HuggingFace all-mpnet-base-v2)

Revision ID: embeddings_002
Revises: memory_agent_001
Create Date: 2026-04-10 00:00:00.000000

Strategy: DROP + recreate (no production rows — backfill script regenerates all embeddings).
Drop order: lesson_chunk_embeddings first (FK child), then note_embeddings.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'embeddings_002'
down_revision = 'memory_agent_001'
branch_labels = None
depends_on = None

# New embedding dimensions: HuggingFace all-mpnet-base-v2
EMBEDDING_DIMENSIONS = 768


def upgrade():
    # 1. Drop HNSW indexes first (must drop before dropping tables)
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_embeddings_vector')
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_vector')

    # 2. Drop regular indexes on lesson_chunk_embeddings
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_unique')
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_lesson_id')

    # 3. Drop regular indexes on note_embeddings
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_user_note')
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_note_type')
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_user_id')

    # 4. Drop lesson_chunk_embeddings first (FK child of lessons)
    op.execute('DROP TABLE IF EXISTS lesson_chunk_embeddings')

    # 5. Drop note_embeddings
    op.execute('DROP TABLE IF EXISTS note_embeddings')

    # 6. Recreate note_embeddings with Vector(768)
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

    # 7. Recreate indexes for note_embeddings
    op.create_index('idx_note_embeddings_user_id', 'note_embeddings', ['user_id'])
    op.create_index('idx_note_embeddings_note_type', 'note_embeddings', ['note_type'])
    op.create_index('idx_note_embeddings_user_note', 'note_embeddings', ['user_id', 'note_id'], unique=True)

    # 8. Recreate HNSW index for note_embeddings (cosine distance, same params as embeddings_001)
    op.execute("""
        CREATE INDEX idx_note_embeddings_vector
        ON note_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # 9. Recreate lesson_chunk_embeddings with Vector(768) and FK to lessons
    op.create_table(
        'lesson_chunk_embeddings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('lesson_id', sa.BigInteger(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], ondelete='CASCADE'),
    )

    # 10. Recreate indexes for lesson_chunk_embeddings
    op.create_index('idx_lesson_chunk_lesson_id', 'lesson_chunk_embeddings', ['lesson_id'])
    op.create_index('idx_lesson_chunk_unique', 'lesson_chunk_embeddings', ['lesson_id', 'chunk_index'], unique=True)

    # 11. Recreate HNSW index for lesson_chunk_embeddings
    op.execute("""
        CREATE INDEX idx_lesson_chunk_embeddings_vector
        ON lesson_chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    raise NotImplementedError(
        "Downgrade not supported — run: alembic downgrade embeddings_001 to restore pre-Phase-10 state"
    )
