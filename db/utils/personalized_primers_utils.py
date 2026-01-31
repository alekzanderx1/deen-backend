"""Helper utilities for personalized primers freshness checking and hashing"""
from typing import List, Optional
from datetime import datetime, timedelta
import hashlib
import json

from ..models.personalized_primers import PersonalizedPrimer
from ..models.lessons import Lesson


def is_primer_fresh(
    primer: PersonalizedPrimer,
    lesson: Lesson,
    user_memory_version: Optional[datetime] = None
) -> bool:
    """
    Check if a cached primer is still fresh.

    A primer is considered fresh if:
    1. It's not marked as stale
    2. TTL hasn't expired
    3. Lesson hasn't been updated since primer was generated
    4. User memory hasn't been updated since primer was generated (if applicable)
    """
    now = datetime.utcnow()

    # Check if manually marked as stale
    if primer.stale:
        return False

    # Check TTL expiration
    if primer.ttl_expires_at < now:
        return False

    # Check if lesson was updated after primer was generated
    if lesson.updated_at and primer.lesson_version < lesson.updated_at:
        return False

    # Check if user memory was updated after primer was generated
    if user_memory_version and primer.memory_version < user_memory_version:
        return False

    return True


def compute_inputs_hash(
    lesson_summary: str,
    lesson_tags: List[str],
    note_ids: List[str],
    ttl_bucket: str
) -> str:
    """
    Compute a hash of the inputs used for generation.

    This helps detect when regeneration is needed due to input changes.
    TTL bucket (e.g., "2026-01-19") groups primers generated on the same day.
    """
    # Sort lists for consistent hashing
    sorted_tags = sorted(lesson_tags or [])
    sorted_note_ids = sorted(note_ids or [])

    # Create input dictionary
    inputs = {
        "lesson_summary": lesson_summary or "",
        "lesson_tags": sorted_tags,
        "note_ids": sorted_note_ids,
        "ttl_bucket": ttl_bucket
    }

    # Convert to JSON string and hash
    json_str = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


def calculate_ttl_expiration(
    generated_at: datetime,
    ttl_days: int = 5
) -> datetime:
    """Calculate TTL expiration timestamp (default 5 days from generation)"""
    return generated_at + timedelta(days=ttl_days)


def get_ttl_bucket(timestamp: datetime) -> str:
    """Get TTL bucket string (date only) for grouping primers generated on the same day"""
    return timestamp.strftime("%Y-%m-%d")
