from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class LessonContentBase(BaseModel):
    lesson_id: Optional[int] = None
    order_position: Optional[int] = None
    title: Optional[str] = None
    content_type: Optional[str] = None
    content_body: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None
    media_urls: Optional[List[str]] = None
    est_minutes: Optional[int] = None


class LessonContentCreate(LessonContentBase):
    lesson_id: int
    order_position: int


class LessonContentUpdate(LessonContentBase):
    pass


class LessonContentRead(LessonContentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
