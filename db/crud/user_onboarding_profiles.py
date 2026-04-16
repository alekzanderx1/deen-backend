from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..models.user_onboarding_profiles import UserOnboardingProfile
from ..schemas.user_onboarding_profiles import OnboardingSubmitRequest


def get_by_user_id(db: Session, user_id: str) -> Optional[UserOnboardingProfile]:
    return db.get(UserOnboardingProfile, user_id)


def upsert(db: Session, user_id: str, payload: OnboardingSubmitRequest) -> UserOnboardingProfile:
    existing = db.get(UserOnboardingProfile, user_id)
    now = datetime.now(timezone.utc)
    if existing:
        existing.tradition = payload.tradition
        existing.goals = payload.goals
        existing.knowledge_level = payload.knowledge_level
        existing.topics = payload.topics
        existing.updated_at = now
    else:
        existing = UserOnboardingProfile(
            user_id=user_id,
            tradition=payload.tradition,
            goals=payload.goals,
            knowledge_level=payload.knowledge_level,
            topics=payload.topics,
            completed_at=now,
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing
