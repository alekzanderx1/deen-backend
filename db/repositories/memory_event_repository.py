from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from agents.models.user_memory_models import MemoryEvent


class MemoryEventRepository:
    """Persistence helpers for MemoryEvent records."""

    def create(
        self,
        db: Session,
        *,
        user_memory_profile_id: str,
        event_type: str,
        event_data: dict,
        trigger_context: Optional[dict] = None,
        processing_status: str = "pending",
        notes_added: Optional[list] = None,
        processing_reasoning: Optional[str] = None,
        processed_at: Optional[datetime] = None,
    ) -> MemoryEvent:
        event = MemoryEvent(
            user_memory_profile_id=user_memory_profile_id,
            event_type=event_type,
            event_data=event_data,
            trigger_context=trigger_context,
            processing_status=processing_status,
            notes_added=notes_added or [],
            processing_reasoning=processing_reasoning,
            processed_at=processed_at,
        )
        db.add(event)
        return event

    def update_status(
        self,
        db: Session,
        event: MemoryEvent,
        *,
        status: str,
        reasoning: Optional[str] = None,
        notes_added: Optional[list] = None,
        processed_at: Optional[datetime] = None,
    ) -> MemoryEvent:
        event.processing_status = status
        if reasoning is not None:
            event.processing_reasoning = reasoning
        if notes_added is not None:
            event.notes_added = notes_added
        event.processed_at = processed_at or datetime.utcnow()
        return event
