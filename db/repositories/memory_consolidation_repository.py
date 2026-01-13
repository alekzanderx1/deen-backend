from typing import List, Optional
from sqlalchemy.orm import Session

from agents.models.user_memory_models import MemoryConsolidation


class MemoryConsolidationRepository:
    """Persistence helpers for MemoryConsolidation records."""

    def get_last(self, db: Session, profile_id: str) -> Optional[MemoryConsolidation]:
        return (
            db.query(MemoryConsolidation)
            .filter(MemoryConsolidation.user_memory_profile_id == profile_id)
            .order_by(MemoryConsolidation.created_at.desc())
            .first()
        )

    def list_recent(self, db: Session, profile_id: str, limit: int = 5) -> List[MemoryConsolidation]:
        return (
            db.query(MemoryConsolidation)
            .filter(MemoryConsolidation.user_memory_profile_id == profile_id)
            .order_by(MemoryConsolidation.created_at.desc())
            .limit(limit)
            .all()
        )

    def log(
        self,
        db: Session,
        *,
        profile_id: str,
        consolidation_type: str,
        notes_before_count: int,
        notes_after_count: int,
        consolidated_notes: list,
        removed_notes: list,
        new_summary_notes: list,
        consolidation_reasoning: str,
    ) -> MemoryConsolidation:
        log_entry = MemoryConsolidation(
            user_memory_profile_id=profile_id,
            consolidation_type=consolidation_type,
            notes_before_count=notes_before_count,
            notes_after_count=notes_after_count,
            consolidated_notes=consolidated_notes,
            removed_notes=removed_notes,
            new_summary_notes=new_summary_notes,
            consolidation_reasoning=consolidation_reasoning,
        )
        db.add(log_entry)
        return log_entry
