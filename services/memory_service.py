from datetime import datetime
from typing import Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from db.repositories.memory_profile_repository import MemoryProfileRepository
from db.repositories.memory_event_repository import MemoryEventRepository
from agents.models.user_memory_models import UserMemoryProfile, MemoryEvent


class MemoryService:
    """
    Coordinates memory profile and event persistence.
    Keeps commit/rollback control in the service/agent layer.
    """

    def __init__(
        self,
        db: Session,
        profile_repo: Optional[MemoryProfileRepository] = None,
        event_repo: Optional[MemoryEventRepository] = None,
    ):
        self.db = db
        self.profile_repo = profile_repo or MemoryProfileRepository()
        self.event_repo = event_repo or MemoryEventRepository()

    def get_or_create_profile(self, user_id: str) -> UserMemoryProfile:
        profile = self.profile_repo.get_by_user_id(self.db, user_id)
        if profile:
            return profile
        profile = self.profile_repo.create(
            self.db,
            user_id=user_id,
            defaults={
                "learning_notes": [],
                "interest_notes": [],
                "knowledge_notes": [],
                "behavior_notes": [],
                "preference_notes": [],
            },
        )
        # No commit here; caller controls commit boundary
        self.db.flush()
        return profile

    def add_notes(self, profile: UserMemoryProfile, new_notes: List[Dict]) -> UserMemoryProfile:
        # Stamp notes
        stamped_notes = []
        for note in new_notes:
            note_copy = dict(note)
            note_copy["id"] = note_copy.get("id") or str(uuid.uuid4())
            note_copy["created_at"] = note_copy.get("created_at") or datetime.utcnow().isoformat()
            stamped_notes.append(note_copy)

        # Build updated lists
        learning_notes = (profile.learning_notes or []).copy()
        knowledge_notes = (profile.knowledge_notes or []).copy()
        interest_notes = (profile.interest_notes or []).copy()
        behavior_notes = (profile.behavior_notes or []).copy()
        preference_notes = (profile.preference_notes or []).copy()

        for note in stamped_notes:
            note_type = note.get("note_type", "learning_notes")
            if note_type == "learning_notes":
                learning_notes.append(note)
            elif note_type == "knowledge_notes":
                knowledge_notes.append(note)
            elif note_type == "interest_notes":
                interest_notes.append(note)
            elif note_type == "behavior_notes":
                behavior_notes.append(note)
            elif note_type == "preference_notes":
                preference_notes.append(note)

        self.profile_repo.update_note_lists(
            self.db,
            profile,
            learning_notes=learning_notes,
            knowledge_notes=knowledge_notes,
            interest_notes=interest_notes,
            behavior_notes=behavior_notes,
            preference_notes=preference_notes,
        )

        # Metadata updates
        profile.total_interactions += 1
        now = datetime.utcnow()
        self.profile_repo.touch_metadata(
            self.db,
            profile,
            last_significant_update=now,
            updated_at=now,
        )

        return profile

    def create_event(
        self,
        *,
        profile_id: str,
        event_type: str,
        event_data: dict,
        trigger_context: Optional[dict],
        processing_status: str = "pending",
    ) -> MemoryEvent:
        event = self.event_repo.create(
            self.db,
            user_memory_profile_id=profile_id,
            event_type=event_type,
            event_data=event_data,
            trigger_context=trigger_context,
            processing_status=processing_status,
        )
        # Ensure we have an ID available immediately
        self.db.flush()
        return event

    def update_event_status(
        self,
        event: MemoryEvent,
        *,
        status: str,
        reasoning: Optional[str] = None,
        notes_added: Optional[list] = None,
    ) -> MemoryEvent:
        return self.event_repo.update_status(
            self.db,
            event,
            status=status,
            reasoning=reasoning,
            notes_added=notes_added,
        )

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
