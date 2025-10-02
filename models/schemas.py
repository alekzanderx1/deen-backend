from pydantic import BaseModel

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