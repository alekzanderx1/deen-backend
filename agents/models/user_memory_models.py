from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class UserMemoryProfile(Base):
    """
    Core user memory profile with flexible, AI-driven note system
    """
    __tablename__ = "user_memory_profiles"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Basic profile info (optional, can be null initially)
    display_name = Column(String)
    preferred_language = Column(String, default="english")
    timezone = Column(String)
    
    # Dynamic memory storage - the key innovation
    learning_notes = Column(JSON, default=list)  # AI-generated learning insights
    interest_notes = Column(JSON, default=list)  # What user is interested in
    knowledge_notes = Column(JSON, default=list)  # What user knows/doesn't know
    behavior_notes = Column(JSON, default=list)  # Learning patterns and behaviors
    preference_notes = Column(JSON, default=list)  # User preferences and style
    
    # Metadata for memory management
    total_interactions = Column(Integer, default=0)
    last_significant_update = Column(DateTime, default=datetime.utcnow)
    memory_version = Column(Integer, default=1)  # For tracking major memory updates
    
    # Relationships
    memory_events = relationship("MemoryEvent", back_populates="profile")
    memory_consolidations = relationship("MemoryConsolidation", back_populates="profile")

class MemoryEvent(Base):
    """
    Individual events that trigger memory updates
    """
    __tablename__ = "memory_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_memory_profile_id = Column(String, ForeignKey("user_memory_profiles.id"), nullable=False)
    
    # Event details
    event_type = Column(String, nullable=False)  # "questionnaire", "lesson_completion", "quiz_result", "chat_interaction"
    event_data = Column(JSON, nullable=False)  # Raw data from the trigger
    trigger_context = Column(JSON)  # Additional context about what triggered this
    
    # Processing results
    notes_added = Column(JSON, default=list)  # Which notes were added from this event
    memory_updates = Column(JSON, default=list)  # What memory changes were made
    processing_reasoning = Column(Text)  # AI's reasoning for memory updates
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    processing_status = Column(String, default="pending")  # "pending", "processed", "failed"
    
    # Relationships
    profile = relationship("UserMemoryProfile", back_populates="memory_events")

class MemoryConsolidation(Base):
    """
    Periodic consolidation of memory to manage context size and improve organization
    """
    __tablename__ = "memory_consolidations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_memory_profile_id = Column(String, ForeignKey("user_memory_profiles.id"), nullable=False)
    
    # Consolidation details
    consolidation_type = Column(String, nullable=False)  # "periodic", "triggered", "emergency"
    notes_before_count = Column(Integer)  # Total notes before consolidation
    notes_after_count = Column(Integer)  # Total notes after consolidation
    
    # What was consolidated
    consolidated_notes = Column(JSON)  # Notes that were merged/summarized
    removed_notes = Column(JSON)  # Notes that were removed as redundant
    new_summary_notes = Column(JSON)  # New summary notes created
    
    # Processing details
    consolidation_reasoning = Column(Text)  # AI's reasoning for consolidation decisions
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserMemoryProfile", back_populates="memory_consolidations")

# Note structure for JSON fields (for documentation)
"""
Note Structure:
{
    "id": "uuid",
    "content": "AI-generated note content",
    "confidence": 0.8,  # How confident the AI is about this note (0.0-1.0)
    "source_event": "lesson_completion",  # What triggered this note
    "created_at": "2024-01-01T12:00:00Z",
    "tags": ["prayer", "beginner", "struggling"],  # AI-generated tags
    "evidence": "User completed Basic Prayer lesson but scored 60% on quiz",
    "relevance_score": 0.9,  # How relevant this note is (for prioritization)
    "category": "knowledge_gap"  # AI-determined category
}

Event Data Examples:
1. Questionnaire: {
    "questions": [...],
    "answers": [...],
    "completion_time": 300
}

2. Lesson Completion: {
    "lesson_id": "basic-prayer-001",
    "lesson_title": "Introduction to Prayer",
    "lesson_tags": ["prayer", "fiqh", "beginner"],
    "lesson_summary": "...",
    "completion_time": 1200,
    "engagement_indicators": {...}
}

3. Quiz Result: {
    "quiz_id": "prayer-quiz-001",
    "lesson_id": "basic-prayer-001",
    "score": 0.75,
    "total_questions": 10,
    "correct_answers": 7,
    "question_details": [...],
    "time_taken": 300
}

4. Chat Interaction: {
    "session_id": "...",
    "user_query": "What is the difference between Sunni and Shia prayer?",
    "response_generated": true,
    "topics_identified": ["prayer", "sectarian_differences"],
    "complexity_level": "intermediate"
}
"""
