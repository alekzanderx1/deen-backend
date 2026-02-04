"""
Migration script to generate embeddings for existing notes and lesson content.
Run this after the database migration to backfill embeddings.

Each lesson_content row (title + content_body) becomes a separate chunk embedding,
preserving the natural structure of the lesson content.

Usage:
    python scripts/migrate_embeddings.py
    python scripts/migrate_embeddings.py --batch-size 100
    python scripts/migrate_embeddings.py --lessons-only
    python scripts/migrate_embeddings.py --notes-only
    python scripts/migrate_embeddings.py --user-id <user_id>
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from tqdm import tqdm

from db.session import SessionLocal
from db.models.lessons import Lesson
from agents.models.user_memory_models import UserMemoryProfile
from services.embedding_service import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_lesson_embeddings(db: Session, batch_size: int = 50) -> Dict[str, int]:
    """
    Generate chunk embeddings for all lessons using lesson_content rows.

    Each lesson_content row (title + content_body) becomes a separate chunk
    embedding, preserving the natural structure of the lesson.

    Returns:
        Dictionary with 'processed', 'chunks', 'skipped', and 'errors' counts
    """
    from db.models.lesson_content import LessonContent
    from sqlalchemy import func

    embedding_service = EmbeddingService(db)

    # Get all lessons that have lesson_content
    lessons_with_content = db.query(Lesson.id).join(
        LessonContent, Lesson.id == LessonContent.lesson_id
    ).distinct().all()

    lesson_ids = [l[0] for l in lessons_with_content]
    total_lessons = len(lesson_ids)

    # Get total lessons for skip count
    all_lessons_count = db.query(Lesson).count()

    logger.info(f"Found {total_lessons} lessons with content to process")
    logger.info(f"Skipping {all_lessons_count - total_lessons} lessons without content")

    processed = 0
    total_chunks = 0
    errors = 0

    for lesson_id in tqdm(lesson_ids, desc="Processing lessons"):
        try:
            chunks = embedding_service.store_lesson_chunk_embeddings(
                lesson_id=lesson_id
            )
            processed += 1
            total_chunks += len(chunks)

            # Commit in batches
            if processed % batch_size == 0:
                db.commit()
                logger.info(f"Committed batch | processed={processed}/{total_lessons} | chunks={total_chunks}")

        except Exception as e:
            errors += 1
            logger.error(f"Failed to process lesson {lesson_id}: {e}")

    # Final commit
    db.commit()

    skipped = all_lessons_count - total_lessons

    logger.info(
        f"Lesson migration complete | processed={processed} | "
        f"chunks={total_chunks} | skipped={skipped} | errors={errors}"
    )
    return {"processed": processed, "chunks": total_chunks, "skipped": skipped, "errors": errors}


def migrate_user_note_embeddings(
    db: Session,
    batch_size: int = 100,
    user_id: str = None
) -> Dict[str, int]:
    """
    Generate embeddings for all user notes.

    Args:
        db: Database session
        batch_size: Number of notes to commit at once
        user_id: Optional specific user ID to migrate (default: all users)

    Returns:
        Dictionary with 'processed' and 'errors' counts
    """
    embedding_service = EmbeddingService(db)

    # Get user memory profiles
    query = db.query(UserMemoryProfile)
    if user_id:
        query = query.filter(UserMemoryProfile.user_id == user_id)

    profiles = query.all()
    total_profiles = len(profiles)
    logger.info(f"Found {total_profiles} user profiles to process")

    total_processed = 0
    total_skipped = 0
    total_errors = 0

    for profile in tqdm(profiles, desc="Processing user profiles"):
        profile_user_id = profile.user_id

        # Process each note type
        note_types = [
            ("learning_notes", profile.learning_notes),
            ("interest_notes", profile.interest_notes),
            ("knowledge_notes", profile.knowledge_notes),
            ("behavior_notes", profile.behavior_notes),
            ("preference_notes", profile.preference_notes),
        ]

        for note_type, notes in note_types:
            if not notes:
                continue

            # Filter notes with content
            valid_notes = [
                note for note in notes
                if note.get("id") and note.get("content")
            ]

            if not valid_notes:
                continue

            try:
                embeddings = embedding_service.store_note_embeddings_batch(
                    user_id=profile_user_id,
                    notes=valid_notes,
                    note_type=note_type
                )
                total_processed += len(embeddings)
                total_skipped += len(notes) - len(valid_notes)

            except Exception as e:
                total_errors += 1
                logger.error(
                    f"Failed to process {note_type} for user {profile_user_id}: {e}"
                )

        # Commit after each user
        db.commit()

    logger.info(
        f"Note migration complete | processed={total_processed} | "
        f"skipped={total_skipped} | errors={total_errors}"
    )
    return {"processed": total_processed, "skipped": total_skipped, "errors": total_errors}


def get_migration_stats(db: Session) -> Dict[str, Any]:
    """Get current migration statistics."""
    from db.models.embeddings import NoteEmbedding, LessonChunkEmbedding
    from sqlalchemy import func

    total_lessons = db.query(Lesson).count()

    # Count lessons with chunks and total chunks
    lessons_with_chunks = db.query(
        func.count(func.distinct(LessonChunkEmbedding.lesson_id))
    ).scalar()
    total_chunks = db.query(LessonChunkEmbedding).count()

    total_profiles = db.query(UserMemoryProfile).count()
    note_embeddings = db.query(NoteEmbedding).count()
    unique_users_with_embeddings = db.query(NoteEmbedding.user_id).distinct().count()

    return {
        "total_lessons": total_lessons,
        "lessons_with_chunks": lessons_with_chunks,
        "total_lesson_chunks": total_chunks,
        "lesson_coverage": f"{(lessons_with_chunks / total_lessons * 100):.1f}%" if total_lessons > 0 else "N/A",
        "total_profiles": total_profiles,
        "note_embeddings": note_embeddings,
        "users_with_embeddings": unique_users_with_embeddings,
        "user_coverage": f"{(unique_users_with_embeddings / total_profiles * 100):.1f}%" if total_profiles > 0 else "N/A",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate existing data to generate embeddings"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for commits (default: 50)"
    )
    parser.add_argument(
        "--lessons-only",
        action="store_true",
        help="Only migrate lessons"
    )
    parser.add_argument(
        "--notes-only",
        action="store_true",
        help="Only migrate notes"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Migrate notes for a specific user only"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show migration statistics"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Embedding Migration Script")
    logger.info("=" * 60)
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}")

    db = SessionLocal()

    try:
        # Show stats if requested
        if args.stats_only:
            stats = get_migration_stats(db)
            logger.info("Current Migration Statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            return

        # Show initial stats
        logger.info("\nInitial state:")
        initial_stats = get_migration_stats(db)
        for key, value in initial_stats.items():
            logger.info(f"  {key}: {value}")

        results = {"lessons": None, "notes": None}

        # Migrate lessons
        if not args.notes_only:
            logger.info("\n" + "-" * 40)
            logger.info("Migrating lesson embeddings...")
            results["lessons"] = migrate_lesson_embeddings(db, args.batch_size)

        # Migrate notes
        if not args.lessons_only:
            logger.info("\n" + "-" * 40)
            logger.info("Migrating note embeddings...")
            results["notes"] = migrate_user_note_embeddings(
                db,
                args.batch_size,
                args.user_id
            )

        # Show final stats
        logger.info("\n" + "-" * 40)
        logger.info("Final state:")
        final_stats = get_migration_stats(db)
        for key, value in final_stats.items():
            logger.info(f"  {key}: {value}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary:")
        if results["lessons"]:
            logger.info(f"  Lessons: {results['lessons']}")
        if results["notes"]:
            logger.info(f"  Notes: {results['notes']}")
        logger.info(f"Completed at: {datetime.utcnow().isoformat()}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
