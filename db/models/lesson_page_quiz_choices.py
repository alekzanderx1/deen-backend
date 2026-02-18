from sqlalchemy import Column, BigInteger, Integer, Text, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.sql import func
from ..session import Base


class LessonPageQuizChoice(Base):
    __tablename__ = "lesson_page_quiz_choices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    question_id = Column(
        BigInteger,
        ForeignKey("lesson_page_quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    choice_key = Column(Text, nullable=False)
    choice_text = Column(Text, nullable=False)
    order_position = Column(Integer, nullable=False, server_default="1")
    is_correct = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
