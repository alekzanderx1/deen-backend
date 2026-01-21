from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatRequest(BaseModel):
    user_query: str
    session_id: str
    language: str

class ElaborationRequest(BaseModel):
    selected_text: str
    context_text: str
    hikmah_tree_name: str
    lesson_name: str
    lesson_summary: str
    user_id: str = None  # Optional: If provided, memory agent will take notes

class ReferenceRequest(BaseModel):
    user_query: str

# schemas for Primers API

class PersonalizedPrimerRequest(BaseModel):
    user_id: str
    lesson_id: int
    force_refresh: bool = False


class PersonalizedPrimerResponse(BaseModel):
    personalized_bullets: List[str]
    generated_at: Optional[datetime] = None
    from_cache: bool
    stale: bool = False
    personalized_available: bool


class BaselinePrimerResponse(BaseModel):
    lesson_id: int
    baseline_bullets: List[str]
    glossary: dict = {}
    updated_at: Optional[datetime] = None
