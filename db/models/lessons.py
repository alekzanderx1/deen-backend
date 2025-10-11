from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from ..session import Base

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    slug = Column(Text, unique=True)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    tags = Column(ARRAY(Text))                  # ["tajweed","quran"]
    status = Column(Text)
    language_code = Column(Text)
    author_user_id = Column(BigInteger)
    estimated_minutes = Column(Integer)
    published_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    hikmah_tree_id = Column(BigInteger)
    order_position = Column(Integer)
