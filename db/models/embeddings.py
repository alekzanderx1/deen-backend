"""
SQLAlchemy models for storing embeddings using pgvector.

These tables store pre-computed embeddings for:
- User memory notes (for semantic similarity search)
- Lesson chunks (for matching notes to lessons via chunked content)
"""

from sqlalchemy import Column, String, BigInteger, Integer, Text, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from ..session import Base

# Embedding dimensions for OpenAI text-embedding-3-small
EMBEDDING_DIMENSIONS = 1536

# Chunking configuration
CHUNK_SIZE = 256  # tokens
CHUNK_OVERLAP = 50  # tokens


class NoteEmbedding(Base):
    """
    Stores embeddings for individual user memory notes.

    Each note in UserMemoryProfile (learning_notes, interest_notes, etc.)
    gets a single embedding stored here for semantic similarity search.
    """
    __tablename__ = "note_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128), nullable=False, index=True)
    note_id = Column(String(128), nullable=False)  # References note's id field in JSON
    note_type = Column(String(50), nullable=False, index=True)  # learning_notes, interest_notes, etc.
    content_hash = Column(String(64), nullable=False)  # SHA256 of note content (for change detection)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_note_embeddings_user_note', 'user_id', 'note_id', unique=True),
    )


class LessonChunkEmbedding(Base):
    """
    Stores embeddings for lesson content chunks.

    Lessons are split into chunks (256 tokens with 50 overlap) and each chunk
    gets its own embedding. This allows for more granular semantic matching
    between user notes and specific parts of a lesson.
    """
    __tablename__ = "lesson_chunk_embeddings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lesson_id = Column(
        BigInteger,
        ForeignKey('lessons.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    chunk_index = Column(Integer, nullable=False)  # Order of chunk within lesson (0, 1, 2, ...)
    chunk_text = Column(Text, nullable=False)  # The actual chunk content
    content_hash = Column(String(64), nullable=False)  # SHA256 of full lesson content (for change detection)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_lesson_chunk_lesson_id', 'lesson_id'),
        Index('idx_lesson_chunk_unique', 'lesson_id', 'chunk_index', unique=True),
    )
