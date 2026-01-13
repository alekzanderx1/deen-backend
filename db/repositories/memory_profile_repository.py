from typing import Optional
from sqlalchemy.orm import Session

from agents.models.user_memory_models import UserMemoryProfile


class MemoryProfileRepository:
    """Persistence helpers for UserMemoryProfile."""

    def get_by_user_id(self, db: Session, user_id: str) -> Optional[UserMemoryProfile]:
        return db.query(UserMemoryProfile).filter(UserMemoryProfile.user_id == user_id).first()

    def create(self, db: Session, user_id: str, defaults: Optional[dict] = None) -> UserMemoryProfile:
        profile = UserMemoryProfile(user_id=user_id, **(defaults or {}))
        db.add(profile)
        return profile

    def update_note_lists(
        self,
        db: Session,
        profile: UserMemoryProfile,
        *,
        learning_notes=None,
        knowledge_notes=None,
        interest_notes=None,
        behavior_notes=None,
        preference_notes=None,
    ) -> UserMemoryProfile:
        if learning_notes is not None:
            profile.learning_notes = learning_notes
        if knowledge_notes is not None:
            profile.knowledge_notes = knowledge_notes
        if interest_notes is not None:
            profile.interest_notes = interest_notes
        if behavior_notes is not None:
            profile.behavior_notes = behavior_notes
        if preference_notes is not None:
            profile.preference_notes = preference_notes
        return profile

    def touch_metadata(self, db: Session, profile: UserMemoryProfile, **fields) -> UserMemoryProfile:
        for key, value in fields.items():
            setattr(profile, key, value)
        return profile
