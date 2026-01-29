from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    user_query: str
    session_id: str
    language: str
    config: Optional[Dict[str, Any]] = None  # Optional agent configuration for agentic endpoint

class ElaborationRequest(BaseModel):
    selected_text: str
    context_text: str
    hikmah_tree_name: str
    lesson_name: str
    lesson_summary: str
    user_id: str = None  # Optional: If provided, memory agent will take notes

class ReferenceRequest(BaseModel):
    user_query: str