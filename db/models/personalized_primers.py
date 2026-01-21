from sqlalchemy import Column, String, BigInteger, Text, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from ..session import Base


class PersonalizedPrimer(Base):
    __tablename__ = "personalized_primers"

    # Composite primary key
    user_id = Column(String(128), primary_key=True, nullable=False)
    lesson_id = Column(BigInteger, ForeignKey('lessons.id', ondelete='CASCADE'), primary_key=True, nullable=False)

    # Content
    personalized_bullets = Column(JSONB, nullable=False)  # Array of 2-3 personalized bullet strings

    # Metadata for caching and freshness
    generated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    inputs_hash = Column(Text, nullable=False)  # Hash of inputs used for generation (for deduplication)
    lesson_version = Column(TIMESTAMP(timezone=True), nullable=False)  # Lesson's updated_at when generated
    memory_version = Column(TIMESTAMP(timezone=True), nullable=False)  # User memory version when generated
    ttl_expires_at = Column(TIMESTAMP(timezone=True), nullable=False)  # TTL expiration timestamp
    stale = Column(Boolean, nullable=False, server_default='false')  # Manually marked as stale

    # Relationship to Lesson (optional)
    lesson = relationship("Lesson", foreign_keys=[lesson_id])
