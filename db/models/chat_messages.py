from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, ForeignKey, CheckConstraint, Index
from sqlalchemy.sql import func
from ..session import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        Index("idx_chat_messages_session_id_id", "chat_session_id", "id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_session_id = Column(
        BigInteger,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
