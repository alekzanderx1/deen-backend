import logging
import traceback

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core import pipeline
from core.logging_config import setup_logging
from db.session import get_db
from models.schemas import (
    ElaborationRequest,
    LessonPageQuizQuestionsResponse,
    QuizSubmissionAckResponse,
    SubmitLessonPageQuizAnswerRequest,
)
from services.hikmah_quiz_service import (
    HikmahQuizService,
    process_quiz_submission_background,
)

setup_logging()
logger = logging.getLogger("api.hikmah")

hikmah_router = APIRouter(
    prefix="/hikmah",
    tags=["hikmah"]
)


@hikmah_router.post("/elaborate/stream")
async def chat_pipeline_stream_ep(request: ElaborationRequest):
    """
    Streaming endpoint to get explanation on selected text in a hikam tree lesson.
    Expects:
      {
        "selected_text": "What does Islam say about justice?",
        "context_text": "The full lesson text...",
        "hikmah_tree_name": "Hikam of Imam Ali",
        "lesson_name": "Justice and Fairness",
        "lesson_summary": "A brief summary of the lesson",
        "user_id": "user123"  // Optional: For memory agent to take notes
      }
    """

    try:
        logger.info(
            "Hikmah elaboration request received",
            extra={
                "user_id": request.user_id,
                "selected_text_len": len(request.selected_text or ""),
                "selected_text_preview": (request.selected_text or "")[:120],
                "context_text_len": len(request.context_text or ""),
                "context_text_preview": (request.context_text or "")[:120],
                "lesson_summary_len": len(request.lesson_summary or ""),
                "lesson_summary_preview": (request.lesson_summary or "")[:120],
                "hikmah_tree_name": request.hikmah_tree_name,
                "lesson_name": request.lesson_name,
            },
        )
        # Returns a StreamingResponse from the pipeline
        return pipeline.hikmah_elaboration_pipeline_streaming(
            selected_text=request.selected_text,
            context_text=request.context_text,
            hikmah_tree_name=request.hikmah_tree_name,
            lesson_name=request.lesson_name,
            lesson_summary=request.lesson_summary,
            user_id=request.user_id  # Pass user_id to pipeline for memory integration
        )
    except Exception as e:
        # Log internally; keep response generic
        print("UNHANDLED ERROR in /hikmah/elborate/stream:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@hikmah_router.get(
    "/pages/{lesson_content_id}/quiz-questions",
    response_model=LessonPageQuizQuestionsResponse,
)
async def get_page_quiz_questions(
    lesson_content_id: int,
    db: Session = Depends(get_db),
):
    """Get all active multiple-choice quiz questions associated with a lesson page."""
    try:
        service = HikmahQuizService(db)
        return service.get_questions_for_page(lesson_content_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Lesson content page not found")
    except Exception as e:
        logger.error(
            "Error fetching quiz questions",
            extra={"lesson_content_id": lesson_content_id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@hikmah_router.post(
    "/pages/{lesson_content_id}/quiz-submit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=QuizSubmissionAckResponse,
)
async def submit_page_quiz_answer(
    lesson_content_id: int,
    request: SubmitLessonPageQuizAnswerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Fire-and-forget quiz answer submission endpoint.
    Returns immediately; processing is done asynchronously in the background.
    """
    background_tasks.add_task(
        process_quiz_submission_background,
        lesson_content_id,
        request.user_id,
        request.question_id,
        request.selected_choice_id,
        request.answered_at,
    )

    return QuizSubmissionAckResponse(status="received")
