from typing import List
from datetime import datetime
from pydantic import BaseModel


class PersonalizedPrimerBase(BaseModel):
    """Base schema for personalized primers"""
    user_id: str
    lesson_id: int
    personalized_bullets: List[str]


class PersonalizedPrimerCreate(PersonalizedPrimerBase):
    """Schema for creating a new personalized primer"""
    generated_at: datetime
    inputs_hash: str
    lesson_version: datetime
    memory_version: datetime
    ttl_expires_at: datetime
    stale: bool = False


class PersonalizedPrimerUpdate(BaseModel):
    """Schema for updating an existing personalized primer"""
    personalized_bullets: List[str] | None = None
    generated_at: datetime | None = None
    inputs_hash: str | None = None
    lesson_version: datetime | None = None
    memory_version: datetime | None = None
    ttl_expires_at: datetime | None = None
    stale: bool | None = None


class PersonalizedPrimerRead(PersonalizedPrimerBase):
    """Schema for reading a personalized primer"""
    generated_at: datetime
    inputs_hash: str
    lesson_version: datetime
    memory_version: datetime
    ttl_expires_at: datetime
    stale: bool

    class Config:
        from_attributes = True


class PersonalizedPrimerResponse(BaseModel):
    """Schema for API response with personalized primer"""
    personalized_bullets: List[str]
    generated_at: datetime | None = None
    from_cache: bool
    stale: bool = False
    personalized_available: bool
