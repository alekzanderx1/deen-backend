from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, UniqueConstraint, Index
from sqlalchemy.sql import func
from ..session import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_chat_sessions_user_session"),
        Index("idx_chat_sessions_user_last_message_at", "user_id", "last_message_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    session_id = Column(Text, nullable=False, index=True)
    title = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_message_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
