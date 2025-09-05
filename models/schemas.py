from pydantic import BaseModel

class ChatRequest(BaseModel):
    user_query: str
    session_id: str
    language: str

class ReferenceRequest(BaseModel):
    user_query: str