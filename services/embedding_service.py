"""
Embedding service for generating, storing, and retrieving embeddings.

Uses OpenAI text-embedding-3-small (1536 dimensions) for generating embeddings
and pgvector for storage and similarity search.

Lesson embeddings are stored per lesson_content row (each row is a natural chunk
containing title and content_body from the lesson_content table).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib
import logging

from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    NOTE_FILTER_THRESHOLD,
)
from db.models.embeddings import NoteEmbedding, LessonChunkEmbedding
from db.models.lesson_content import LessonContent

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for managing embeddings for notes and lesson chunks.

    Responsibilities:
    - Generate embeddings using OpenAI API
    - Store embeddings for each lesson_content row (natural chunks)
    - Store single embeddings for user notes
    - Find similar notes by comparing against all lesson content embeddings
    - Handle content hashing for change detection
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ================== EMBEDDING GENERATION ==================

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                dimensions=EMBEDDING_DIMENSIONS
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in a single API call."""
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
                dimensions=EMBEDDING_DIMENSIONS
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    # ================== CONTENT HASHING ==================

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    # ================== NOTE EMBEDDING OPERATIONS ==================

    def store_note_embedding(
        self,
        user_id: str,
        note_id: str,
        note_type: str,
        content: str,
        embedding: Optional[List[float]] = None
    ) -> NoteEmbedding:
        """
        Store or update embedding for a single note.

        Args:
            user_id: User identifier
            note_id: Note's unique ID (from JSON)
            note_type: Type of note (learning_notes, interest_notes, etc.)
            content: Note content text
            embedding: Pre-computed embedding (optional, will generate if not provided)

        Returns:
            NoteEmbedding object
        """
        content_hash = self.compute_content_hash(content)

        # Check if embedding already exists
        existing = self.db.query(NoteEmbedding).filter(
            NoteEmbedding.user_id == user_id,
            NoteEmbedding.note_id == note_id
        ).first()

        if existing:
            # Check if content changed
            if existing.content_hash == content_hash:
                logger.debug(f"Note embedding unchanged | note_id={note_id}")
                return existing

            # Content changed, regenerate embedding
            if embedding is None:
                embedding = self.generate_embedding(content)

            existing.content_hash = content_hash
            existing.embedding = embedding
            existing.updated_at = datetime.utcnow()

            logger.info(f"Updated note embedding | user_id={user_id} | note_id={note_id}")
            return existing

        # Create new embedding
        if embedding is None:
            embedding = self.generate_embedding(content)

        note_embedding = NoteEmbedding(
            user_id=user_id,
            note_id=note_id,
            note_type=note_type,
            content_hash=content_hash,
            embedding=embedding
        )

        self.db.add(note_embedding)
        logger.info(f"Created note embedding | user_id={user_id} | note_id={note_id}")
        return note_embedding

    def store_note_embeddings_batch(
        self,
        user_id: str,
        notes: List[Dict[str, Any]],
        note_type: str
    ) -> List[NoteEmbedding]:
        """
        Store embeddings for multiple notes efficiently.

        Args:
            user_id: User identifier
            notes: List of note dictionaries with 'id' and 'content' fields
            note_type: Type of notes

        Returns:
            List of NoteEmbedding objects
        """
        if not notes:
            return []

        results = []
        notes_to_embed = []
        existing_embeddings = {}

        # Get existing embeddings for these notes
        note_ids = [note.get('id') for note in notes if note.get('id')]
        if note_ids:
            existing = self.db.query(NoteEmbedding).filter(
                NoteEmbedding.user_id == user_id,
                NoteEmbedding.note_id.in_(note_ids)
            ).all()
            existing_embeddings = {e.note_id: e for e in existing}

        # Determine which notes need new/updated embeddings
        for note in notes:
            note_id = note.get('id')
            content = note.get('content', '')

            if not note_id or not content:
                continue

            content_hash = self.compute_content_hash(content)

            if note_id in existing_embeddings:
                existing_emb = existing_embeddings[note_id]
                if existing_emb.content_hash == content_hash:
                    # No change, use existing
                    results.append(existing_emb)
                else:
                    # Content changed, need to re-embed
                    notes_to_embed.append({
                        'note': note,
                        'content_hash': content_hash,
                        'existing': existing_emb
                    })
            else:
                # New note, need to embed
                notes_to_embed.append({
                    'note': note,
                    'content_hash': content_hash,
                    'existing': None
                })

        # Generate embeddings in batch
        if notes_to_embed:
            contents = [item['note'].get('content', '') for item in notes_to_embed]
            embeddings = self.generate_embeddings_batch(contents)

            for i, item in enumerate(notes_to_embed):
                note = item['note']
                content_hash = item['content_hash']
                existing = item['existing']
                embedding = embeddings[i]

                if existing:
                    # Update existing
                    existing.content_hash = content_hash
                    existing.embedding = embedding
                    existing.updated_at = datetime.utcnow()
                    results.append(existing)
                else:
                    # Create new
                    note_embedding = NoteEmbedding(
                        user_id=user_id,
                        note_id=note.get('id'),
                        note_type=note_type,
                        content_hash=content_hash,
                        embedding=embedding
                    )
                    self.db.add(note_embedding)
                    results.append(note_embedding)

            logger.info(
                f"Processed {len(notes_to_embed)} note embeddings | "
                f"user_id={user_id} | note_type={note_type}"
            )

        return results

    def delete_note_embedding(self, user_id: str, note_id: str) -> bool:
        """Delete embedding for a note (when note is deleted)."""
        result = self.db.query(NoteEmbedding).filter(
            NoteEmbedding.user_id == user_id,
            NoteEmbedding.note_id == note_id
        ).delete()
        return result > 0

    def delete_user_embeddings(self, user_id: str) -> int:
        """Delete all embeddings for a user."""
        result = self.db.query(NoteEmbedding).filter(
            NoteEmbedding.user_id == user_id
        ).delete()
        logger.info(f"Deleted {result} note embeddings | user_id={user_id}")
        return result

    # ================== LESSON CHUNK EMBEDDING OPERATIONS ==================

    def store_lesson_chunk_embeddings(
        self,
        lesson_id: int,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[LessonChunkEmbedding]:
        """
        Store embeddings for a lesson using its lesson_content rows as natural chunks.

        Each row in lesson_content (with title + content_body) becomes a separate
        embedding chunk. This preserves the logical structure of the lesson content.

        Args:
            lesson_id: Lesson identifier
            summary: Lesson summary (optional, for backwards compatibility)
            tags: List of lesson tags (optional, for backwards compatibility)

        Returns:
            List of LessonChunkEmbedding objects
        """
        # Get all lesson content rows ordered by position
        lesson_contents = self.db.query(LessonContent).filter(
            LessonContent.lesson_id == lesson_id
        ).order_by(LessonContent.order_position).all()

        if not lesson_contents:
            logger.warning(f"No lesson content found | lesson_id={lesson_id}")
            return []

        # Compute content hash from all lesson content
        combined_content = self._combine_lesson_content_for_hash(lesson_contents)
        content_hash = self.compute_content_hash(combined_content)

        # Check if chunks already exist with same hash
        existing_chunks = self.db.query(LessonChunkEmbedding).filter(
            LessonChunkEmbedding.lesson_id == lesson_id
        ).all()

        if existing_chunks and existing_chunks[0].content_hash == content_hash:
            logger.debug(f"Lesson chunks unchanged | lesson_id={lesson_id}")
            return existing_chunks

        # Delete existing chunks if content changed
        if existing_chunks:
            self.db.query(LessonChunkEmbedding).filter(
                LessonChunkEmbedding.lesson_id == lesson_id
            ).delete()
            logger.info(f"Deleted {len(existing_chunks)} old chunks | lesson_id={lesson_id}")

        # Format each lesson_content row as a chunk
        chunks = []
        for content in lesson_contents:
            chunk_text = self._format_lesson_content_for_embedding(content)
            if chunk_text:
                chunks.append({
                    'index': content.order_position,
                    'text': chunk_text,
                    'content_id': content.id
                })

        if not chunks:
            logger.warning(f"No valid chunks generated for lesson | lesson_id={lesson_id}")
            return []

        # Generate embeddings for all chunks in batch
        chunk_texts = [c['text'] for c in chunks]
        embeddings = self.generate_embeddings_batch(chunk_texts)

        # Store each chunk
        chunk_embeddings = []
        for chunk_info, embedding in zip(chunks, embeddings):
            chunk_embedding = LessonChunkEmbedding(
                lesson_id=lesson_id,
                chunk_index=chunk_info['index'],
                chunk_text=chunk_info['text'],
                content_hash=content_hash,
                embedding=embedding
            )
            self.db.add(chunk_embedding)
            chunk_embeddings.append(chunk_embedding)

        logger.info(
            f"Created {len(chunk_embeddings)} lesson chunks from lesson_content | lesson_id={lesson_id}"
        )
        return chunk_embeddings

    def _combine_lesson_content_for_hash(self, lesson_contents: List[LessonContent]) -> str:
        """Combine all lesson content for hash computation."""
        parts = []
        for content in lesson_contents:
            if content.title:
                parts.append(content.title)
            if content.content_body:
                parts.append(content.content_body)
        return "\n".join(parts)

    def _format_lesson_content_for_embedding(self, content: LessonContent) -> str:
        """Format a lesson_content row for embedding generation."""
        parts = []
        if content.title:
            parts.append(f"Section: {content.title}")
        if content.content_body:
            parts.append(content.content_body)
        return "\n".join(parts) if parts else ""

    def get_lesson_chunk_embeddings(self, lesson_id: int) -> List[LessonChunkEmbedding]:
        """Get all chunk embeddings for a lesson."""
        return self.db.query(LessonChunkEmbedding).filter(
            LessonChunkEmbedding.lesson_id == lesson_id
        ).order_by(LessonChunkEmbedding.chunk_index).all()

    def delete_lesson_chunks(self, lesson_id: int) -> int:
        """Delete all chunk embeddings for a lesson."""
        result = self.db.query(LessonChunkEmbedding).filter(
            LessonChunkEmbedding.lesson_id == lesson_id
        ).delete()
        logger.info(f"Deleted {result} lesson chunks | lesson_id={lesson_id}")
        return result

    # ================== SIMILARITY SEARCH (NEW APPROACH) ==================

    def find_similar_notes_to_lesson(
        self,
        user_id: str,
        lesson_id: int,
        threshold: float = NOTE_FILTER_THRESHOLD,
        note_types: Optional[List[str]] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Find notes similar to a lesson by comparing each note against all lesson chunks.

        For each note, we compute the maximum similarity across all lesson chunks.
        Notes with max similarity >= threshold are included in results.

        Args:
            user_id: User identifier
            lesson_id: Lesson to find similar notes for
            threshold: Minimum similarity score to include a note (default: 0.4)
            note_types: Filter by specific note types (optional)

        Returns:
            List of tuples: (note_id, note_type, max_similarity_score)
        """
        # Get lesson chunk embeddings
        lesson_chunks = self.get_lesson_chunk_embeddings(lesson_id)

        if not lesson_chunks:
            logger.warning(f"No chunk embeddings found for lesson | lesson_id={lesson_id}")
            return []

        # Build query to find notes with max similarity across all chunks
        # For each note, compute similarity to each chunk and take the max
        chunk_conditions = []

        for chunk in lesson_chunks:
            # Embed the vector directly in SQL (not as a parameter) to avoid
            # conflict between SQLAlchemy's :param syntax and PostgreSQL's ::cast syntax
            embedding_str = '[' + ','.join(str(x) for x in chunk.embedding) + ']'
            chunk_conditions.append(
                f"1 - (embedding <=> '{embedding_str}'::vector)"
            )

        # Create GREATEST expression for max similarity across chunks
        max_similarity_expr = f"GREATEST({', '.join(chunk_conditions)})"

        query = text(f"""
            SELECT
                note_id,
                note_type,
                {max_similarity_expr} as max_similarity
            FROM note_embeddings
            WHERE user_id = :user_id
            AND {max_similarity_expr} >= :threshold
            ORDER BY max_similarity DESC
        """)

        result = self.db.execute(query, {'user_id': user_id, 'threshold': threshold})

        similar_notes = []
        for row in result:
            note_id, note_type, max_similarity = row
            if note_types is None or note_type in note_types:
                similar_notes.append((note_id, note_type, float(max_similarity)))

        logger.debug(
            f"Found {len(similar_notes)} similar notes | user_id={user_id} | "
            f"lesson_id={lesson_id} | threshold={threshold} | chunks={len(lesson_chunks)}"
        )

        return similar_notes

    def calculate_signal_quality(
        self,
        filtered_notes: List[Tuple[str, str, float]]
    ) -> float:
        """
        Calculate signal quality as the average similarity of filtered notes.

        Args:
            filtered_notes: List of (note_id, note_type, similarity_score) tuples

        Returns:
            Average similarity score (0.0 - 1.0)
        """
        if not filtered_notes:
            return 0.0

        similarities = [score for _, _, score in filtered_notes]
        return sum(similarities) / len(similarities)

    # ================== EMBEDDING EXISTENCE CHECK ==================

    def has_note_embeddings(self, user_id: str) -> bool:
        """Check if user has any note embeddings."""
        count = self.db.query(NoteEmbedding).filter(
            NoteEmbedding.user_id == user_id
        ).count()
        return count > 0

    def has_lesson_chunks(self, lesson_id: int) -> bool:
        """Check if lesson has chunk embeddings."""
        return self.db.query(LessonChunkEmbedding).filter(
            LessonChunkEmbedding.lesson_id == lesson_id
        ).count() > 0

    def get_note_embedding_count(self, user_id: str) -> int:
        """Get count of embeddings for a user."""
        return self.db.query(NoteEmbedding).filter(
            NoteEmbedding.user_id == user_id
        ).count()

    def get_lesson_chunk_count(self, lesson_id: int) -> int:
        """Get count of chunk embeddings for a lesson."""
        return self.db.query(LessonChunkEmbedding).filter(
            LessonChunkEmbedding.lesson_id == lesson_id
        ).count()

    def get_total_lesson_chunks_count(self) -> int:
        """Get total count of all lesson chunk embeddings."""
        return self.db.query(LessonChunkEmbedding).count()
