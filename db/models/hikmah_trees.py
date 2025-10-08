from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from ..session import Base

class HikmahTree(Base):
    __tablename__ = "hikmah_trees"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text)
    summary = Column(Text)
    tags = Column(ARRAY(Text))
    skill_level = Column(Integer) # ← integer 1..10
    meta = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
