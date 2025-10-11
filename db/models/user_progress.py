from sqlalchemy import Column, BigInteger, Integer, Text, Boolean, TIMESTAMP, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..session import Base

class UserProgress(Base):
    __tablename__ = "user_progress"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(128), index=True)
    hikmah_tree_id = Column(BigInteger)
    lesson_id = Column(BigInteger)
    content_id = Column(BigInteger)
    is_completed = Column(Boolean, server_default="false")
    percent_complete = Column(Numeric(5,2))
    last_position = Column(Integer)
    notes = Column(Text)
    meta = Column(JSONB)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

