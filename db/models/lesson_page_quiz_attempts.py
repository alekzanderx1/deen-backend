from sqlalchemy import Column, BigInteger, String, TIMESTAMP, Boolean, ForeignKey
from sqlalchemy.sql import func
from ..session import Base


class LessonPageQuizAttempt(Base):
    __tablename__ = "lesson_page_quiz_attempts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    lesson_content_id = Column(
        BigInteger,
        ForeignKey("lesson_content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        BigInteger,
        ForeignKey("lesson_page_quiz_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_choice_id = Column(
        BigInteger,
        ForeignKey("lesson_page_quiz_choices.id"),
        nullable=False,
    )
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
