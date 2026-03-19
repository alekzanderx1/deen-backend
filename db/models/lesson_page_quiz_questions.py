from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
from ..session import Base


class LessonPageQuizQuestion(Base):
    __tablename__ = "lesson_page_quiz_questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    lesson_content_id = Column(
        BigInteger,
        ForeignKey("lesson_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt = Column(Text, nullable=False)
    explanation = Column(Text)
    tags = Column(ARRAY(Text))
    order_position = Column(Integer, nullable=False, server_default="1")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
