from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class UserProgressBase(BaseModel):
    user_id: Optional[int] = None
    lesson_id: Optional[int] = None
    content_id: Optional[int] = None
    is_completed: Optional[bool] = None
    percent_complete: Optional[float] = Field(None, ge=0, le=100)
    last_position: Optional[int] = None
    notes: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    hikmah_tree_id: Optional[int] = None

class UserProgressCreate(UserProgressBase):
    user_id: int
    lesson_id: int

class UserProgressUpdate(UserProgressBase):
    pass

class UserProgressRead(UserProgressBase):
    id: int
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
