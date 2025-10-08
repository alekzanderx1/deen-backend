from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class LessonBase(BaseModel):
    slug: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    language_code: Optional[str] = None
    author_user_id: Optional[int] = None
    estimated_minutes: Optional[int] = None
    published_at: Optional[datetime] = None
    hikmah_tree_id: Optional[int] = None
    order_position: Optional[int] = None

class LessonCreate(LessonBase):
    title: str

class LessonUpdate(LessonBase):
    pass

class LessonRead(LessonBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
