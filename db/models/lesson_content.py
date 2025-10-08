from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ..session import Base

class LessonContent(Base):
    __tablename__ = "lesson_content"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lesson_id = Column(BigInteger)
    order_position = Column(Integer, nullable=False)
    title = Column(Text)
    content_type = Column(Text)
    content_body = Column(Text)
    content_json = Column(JSONB)
    media_urls = Column(JSONB)
    est_minutes = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
