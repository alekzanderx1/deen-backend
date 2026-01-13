from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from db.repositories.memory_consolidation_repository import MemoryConsolidationRepository
from db.repositories.memory_profile_repository import MemoryProfileRepository
from agents.models.user_memory_models import UserMemoryProfile, MemoryConsolidation


class ConsolidationService:
    """Coordinates consolidation persistence (history + profile updates)."""

    def __init__(
        self,
        db: Session,
        consolidation_repo: Optional[MemoryConsolidationRepository] = None,
        profile_repo: Optional[MemoryProfileRepository] = None,
    ):
        self.db = db
        self.consolidation_repo = consolidation_repo or MemoryConsolidationRepository()
        self.profile_repo = profile_repo or MemoryProfileRepository()

    def get_last_consolidation(self, profile_id: str) -> Optional[MemoryConsolidation]:
        return self.consolidation_repo.get_last(self.db, profile_id)

    def list_recent_consolidations(self, profile_id: str, limit: int = 5) -> List[MemoryConsolidation]:
        return self.consolidation_repo.list_recent(self.db, profile_id, limit)

    def apply_consolidated_memory(
        self,
        profile: UserMemoryProfile,
        consolidated_memory: dict,
    ) -> UserMemoryProfile:
        self.profile_repo.update_note_lists(
            self.db,
            profile,
            learning_notes=consolidated_memory.get("learning_notes", []),
            knowledge_notes=consolidated_memory.get("knowledge_notes", []),
            interest_notes=consolidated_memory.get("interest_notes", []),
            behavior_notes=consolidated_memory.get("behavior_notes", []),
            preference_notes=consolidated_memory.get("preference_notes", []),
        )
        now = datetime.utcnow()
        profile.memory_version += 1
        self.profile_repo.touch_metadata(
            self.db,
            profile,
            last_significant_update=now,
            updated_at=now,
        )
        return profile

    def log_consolidation(
        self,
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
        entry = self.consolidation_repo.log(
            self.db,
            profile_id=profile_id,
            consolidation_type=consolidation_type,
            notes_before_count=notes_before_count,
            notes_after_count=notes_after_count,
            consolidated_notes=consolidated_notes,
            removed_notes=removed_notes,
            new_summary_notes=new_summary_notes,
            consolidation_reasoning=consolidation_reasoning,
        )
        # Flush so the ID is available
        self.db.flush()
        return entry
