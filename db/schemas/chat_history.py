from datetime import datetime
from typing import List
from pydantic import BaseModel


class SavedChatListItem(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    message_count: int


class SavedChatListResponse(BaseModel):
    items: List[SavedChatListItem]
    total: int
    limit: int
    offset: int


class SavedChatMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class SavedChatDetailResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime
    messages: List[SavedChatMessage]
    total_messages: int
    limit: int
    offset: int
