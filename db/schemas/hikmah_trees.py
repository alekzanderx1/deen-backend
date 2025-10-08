from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class HikmahTreeBase(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    skill_level: Optional[int] = Field(None, ge=1, le=10)
    meta: Optional[Dict[str, Any]] = None


class HikmahTreeCreate(HikmahTreeBase):
    title: str


class HikmahTreeUpdate(HikmahTreeBase):
    pass


class HikmahTreeRead(HikmahTreeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
