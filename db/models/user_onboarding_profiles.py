from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from ..session import Base


class UserOnboardingProfile(Base):
    __tablename__ = "user_onboarding_profiles"

    user_id = Column(String(128), primary_key=True, nullable=False)
    tradition = Column(Text, nullable=False)
    goals = Column(ARRAY(Text), nullable=False)
    knowledge_level = Column(Text, nullable=False)
    topics = Column(ARRAY(Text), nullable=False)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
