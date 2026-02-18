import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from db.models.lesson_content import LessonContent
from db.models.lessons import Lesson
from db.models.lesson_page_quiz_questions import LessonPageQuizQuestion
from db.models.lesson_page_quiz_choices import LessonPageQuizChoice
from db.models.lesson_page_quiz_attempts import LessonPageQuizAttempt
from db.session import SessionLocal

logger = logging.getLogger(__name__)


class HikmahQuizService:
    """Service for lesson-page quiz retrieval and answer processing."""

    def __init__(self, db: Session):
        self.db = db

    def get_questions_for_page(self, lesson_content_id: int) -> Dict[str, Any]:
        """Return all active quiz questions for a lesson content page."""
        page = self.db.get(LessonContent, lesson_content_id)
        if not page:
            raise LookupError("Lesson content page not found")

        questions = (
            self.db.query(LessonPageQuizQuestion)
            .filter(
                LessonPageQuizQuestion.lesson_content_id == lesson_content_id,
                LessonPageQuizQuestion.is_active.is_(True),
            )
            .order_by(LessonPageQuizQuestion.order_position.asc(), LessonPageQuizQuestion.id.asc())
            .all()
        )

        if not questions:
            return {"lesson_content_id": lesson_content_id, "questions": []}

        question_ids = [q.id for q in questions]
        all_choices = (
            self.db.query(LessonPageQuizChoice)
            .filter(LessonPageQuizChoice.question_id.in_(question_ids))
            .order_by(
                LessonPageQuizChoice.question_id.asc(),
                LessonPageQuizChoice.order_position.asc(),
                LessonPageQuizChoice.id.asc(),
            )
            .all()
        )

        choices_by_question: Dict[int, List[LessonPageQuizChoice]] = {}
        for choice in all_choices:
            choices_by_question.setdefault(choice.question_id, []).append(choice)

        response_questions: List[Dict[str, Any]] = []
        for question in questions:
            question_choices = choices_by_question.get(question.id, [])
            correct_choice = next((c for c in question_choices if c.is_correct), None)

            if not correct_choice:
                raise ValueError(
                    f"Quiz question id={question.id} has no correct choice configured"
                )

            response_questions.append(
                {
                    "id": int(question.id),
                    "prompt": question.prompt,
                    "order_position": int(question.order_position),
                    "choices": [
                        {
                            "id": int(choice.id),
                            "choice_key": choice.choice_key,
                            "choice_text": choice.choice_text,
                            "order_position": int(choice.order_position),
                        }
                        for choice in question_choices
                    ],
                    "correct_choice_id": int(correct_choice.id),
                    "explanation": question.explanation,
                }
            )

        return {
            "lesson_content_id": lesson_content_id,
            "questions": response_questions,
        }

    def process_submission(
        self,
        lesson_content_id: int,
        user_id: str,
        question_id: int,
        selected_choice_id: int,
        answered_at: Optional[datetime] = None,
    ) -> None:
        """Process a quiz submission: validate, persist attempt, and trigger memory if needed."""
        page = self.db.get(LessonContent, lesson_content_id)
        if not page:
            logger.warning(
                "Quiz submit ignored: page not found",
                extra={
                    "lesson_content_id": lesson_content_id,
                    "question_id": question_id,
                    "selected_choice_id": selected_choice_id,
                    "user_id": user_id,
                },
            )
            return

        question = (
            self.db.query(LessonPageQuizQuestion)
            .filter(
                LessonPageQuizQuestion.id == question_id,
                LessonPageQuizQuestion.lesson_content_id == lesson_content_id,
                LessonPageQuizQuestion.is_active.is_(True),
            )
            .first()
        )
        if not question:
            logger.warning(
                "Quiz submit ignored: question not found for page",
                extra={
                    "lesson_content_id": lesson_content_id,
                    "question_id": question_id,
                    "selected_choice_id": selected_choice_id,
                    "user_id": user_id,
                },
            )
            return

        selected_choice = (
            self.db.query(LessonPageQuizChoice)
            .filter(
                LessonPageQuizChoice.id == selected_choice_id,
                LessonPageQuizChoice.question_id == question_id,
            )
            .first()
        )
        if not selected_choice:
            logger.warning(
                "Quiz submit ignored: selected choice not found for question",
                extra={
                    "lesson_content_id": lesson_content_id,
                    "question_id": question_id,
                    "selected_choice_id": selected_choice_id,
                    "user_id": user_id,
                },
            )
            return

        correct_choice = (
            self.db.query(LessonPageQuizChoice)
            .filter(
                LessonPageQuizChoice.question_id == question_id,
                LessonPageQuizChoice.is_correct.is_(True),
            )
            .first()
        )
        if not correct_choice:
            logger.warning(
                "Quiz submit ignored: no correct choice configured",
                extra={
                    "lesson_content_id": lesson_content_id,
                    "question_id": question_id,
                    "selected_choice_id": selected_choice_id,
                    "user_id": user_id,
                },
            )
            return

        answered_at_utc = self._to_utc(answered_at)
        is_correct = bool(selected_choice.is_correct)

        attempt = LessonPageQuizAttempt(
            user_id=user_id,
            lesson_content_id=lesson_content_id,
            question_id=question_id,
            selected_choice_id=selected_choice_id,
            is_correct=is_correct,
            answered_at=answered_at_utc,
        )
        self.db.add(attempt)
        self.db.commit()

        if is_correct:
            return

        lesson = self.db.get(Lesson, page.lesson_id) if page.lesson_id else None
        topics_tested = question.tags or (lesson.tags if lesson and lesson.tags else [])

        try:
            asyncio.run(
                self._trigger_incorrect_quiz_memory_event(
                    user_id=user_id,
                    lesson_content_id=lesson_content_id,
                    question=question,
                    selected_choice=selected_choice,
                    correct_choice=correct_choice,
                    lesson_id=page.lesson_id,
                    topics_tested=topics_tested,
                )
            )
        except Exception:
            logger.exception(
                "Failed to process incorrect quiz memory event",
                extra={
                    "lesson_content_id": lesson_content_id,
                    "question_id": question_id,
                    "selected_choice_id": selected_choice_id,
                    "user_id": user_id,
                },
            )

    async def _trigger_incorrect_quiz_memory_event(
        self,
        user_id: str,
        lesson_content_id: int,
        question: LessonPageQuizQuestion,
        selected_choice: LessonPageQuizChoice,
        correct_choice: LessonPageQuizChoice,
        lesson_id: Optional[int],
        topics_tested: List[str],
    ) -> None:
        from agents.core.universal_memory_agent import UniversalMemoryAgent, InteractionType

        memory_agent = UniversalMemoryAgent(self.db)

        quiz_id = f"page:{lesson_content_id}:question:{question.id}"
        interaction_data = {
            "quiz_id": quiz_id,
            "lesson_id": str(lesson_id) if lesson_id is not None else None,
            "score": 0.0,
            "total_questions": 1,
            "correct_answers": 0,
            "topics_tested": topics_tested,
            "incorrect_topics": topics_tested,
            "question_details": [
                {
                    "question_id": int(question.id),
                    "prompt": question.prompt,
                    "selected_choice": {
                        "id": int(selected_choice.id),
                        "key": selected_choice.choice_key,
                        "text": selected_choice.choice_text,
                    },
                    "correct_choice": {
                        "id": int(correct_choice.id),
                        "key": correct_choice.choice_key,
                        "text": correct_choice.choice_text,
                    },
                }
            ],
        }

        context = {
            "source": "hikmah_page_quiz",
            "lesson_content_id": int(lesson_content_id),
            "question_prompt": question.prompt,
            "selected_choice_text": selected_choice.choice_text,
            "correct_choice_text": correct_choice.choice_text,
        }

        await memory_agent.analyze_interaction(
            user_id=user_id,
            interaction_type=InteractionType.QUIZ_RESULT,
            interaction_data=interaction_data,
            context=context,
        )

    @staticmethod
    def _to_utc(value: Optional[datetime]) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def process_quiz_submission_background(
    lesson_content_id: int,
    user_id: str,
    question_id: int,
    selected_choice_id: int,
    answered_at: Optional[datetime] = None,
) -> None:
    """Background-task entry point for fire-and-forget quiz submission handling."""
    db = SessionLocal()
    try:
        service = HikmahQuizService(db)
        service.process_submission(
            lesson_content_id=lesson_content_id,
            user_id=user_id,
            question_id=question_id,
            selected_choice_id=selected_choice_id,
            answered_at=answered_at,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled error processing quiz submission in background",
            extra={
                "lesson_content_id": lesson_content_id,
                "question_id": question_id,
                "selected_choice_id": selected_choice_id,
                "user_id": user_id,
            },
        )
    finally:
        db.close()
