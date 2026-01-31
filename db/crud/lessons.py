import logging
from sqlalchemy.orm import Session

from .base import CRUDBase
from ..models.lessons import Lesson
from ..schemas.lessons import LessonCreate, LessonUpdate

logger = logging.getLogger(__name__)


class CRUDLesson(CRUDBase[Lesson, LessonCreate, LessonUpdate]):
    """CRUD operations for Lesson model with embedding generation."""

    def create(self, db: Session, obj_in: LessonCreate) -> Lesson:
        """Create a new lesson and generate its embedding."""
        lesson = super().create(db, obj_in)

        # Generate embeddings for the lesson's content
        self._update_lesson_embedding(db, lesson)

        return lesson

    def update(self, db: Session, db_obj: Lesson, obj_in: LessonUpdate) -> Lesson:
        """Update a lesson."""
        lesson = super().update(db, db_obj, obj_in)
        return lesson

    def regenerate_embeddings(self, db: Session, lesson: Lesson) -> None:
        """
        Explicitly regenerate embeddings for a lesson.

        Call this after updating lesson_content rows to refresh embeddings.
        """
        self._update_lesson_embedding(db, lesson)

    def _update_lesson_embedding(self, db: Session, lesson: Lesson) -> None:
        """Generate/update chunk embeddings for a lesson from its lesson_content rows."""
        try:
            from services.embedding_service import EmbeddingService

            embedding_service = EmbeddingService(db)
            chunks = embedding_service.store_lesson_chunk_embeddings(
                lesson_id=lesson.id
            )
            db.commit()
            logger.info(f"Generated lesson chunk embeddings | lesson_id={lesson.id} | chunks={len(chunks)}")
        except Exception as e:
            # Log but don't fail the main operation
            logger.error(f"Failed to store lesson chunk embeddings | lesson_id={lesson.id} | error={e}")


lesson_crud = CRUDLesson(Lesson)
