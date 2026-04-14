from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, model_validator


class OnboardingSubmitRequest(BaseModel):
    tradition: str
    goals: List[str]
    knowledge_level: str
    topics: List[str]

    @model_validator(mode="after")
    def validate_lists(self) -> "OnboardingSubmitRequest":
        if not self.goals:
            raise ValueError("goals must not be empty")
        if not self.topics:
            raise ValueError("topics must not be empty")
        if len(self.topics) > 3:
            raise ValueError("topics may contain at most 3 selections")
        return self


class OnboardingRead(BaseModel):
    user_id: str
    tradition: str
    goals: List[str]
    knowledge_level: str
    topics: List[str]
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
