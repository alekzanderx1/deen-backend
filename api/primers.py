from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import logging
import traceback
import json

from db.session import get_db
from db.crud.lessons import lesson_crud
from services.primer_service import PrimerService
from models.schemas import (
    PersonalizedPrimerRequest,
    PersonalizedPrimerResponse,
    BaselinePrimerResponse
)

logger = logging.getLogger(__name__)

primers_router = APIRouter(
    prefix="/primers",
    tags=["primers"]
)


@primers_router.get("/{lesson_id}/baseline", response_model=BaselinePrimerResponse)
async def get_baseline_primer(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    """
    Get baseline primer for a lesson.
    Returns preset bullets and glossary that are shown to all users.
    """
    try:
        logger.info(f"Fetching baseline primer | lesson_id={lesson_id}")

        lesson = lesson_crud.get(db, lesson_id)
        if not lesson:
            logger.warning(f"Lesson not found | lesson_id={lesson_id}")
            raise HTTPException(status_code=404, detail="Lesson not found")

        logger.info(f"Baseline primer fetched successfully | lesson_id={lesson_id}")

        return BaselinePrimerResponse(
            lesson_id=lesson.id,
            baseline_bullets=lesson.baseline_primer_bullets or [],
            glossary=lesson.baseline_primer_glossary or {},
            updated_at=lesson.baseline_primer_updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching baseline primer | lesson_id={lesson_id} | error={str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")


@primers_router.post("/personalized", response_model=PersonalizedPrimerResponse)
async def get_personalized_primer(
    request: PersonalizedPrimerRequest,
    db: Session = Depends(get_db)
):
    """
    Get personalized "For You" primer section.

    Request body:
    - user_id: User identifier
    - lesson_id: Lesson to generate primer for
    - force_refresh: Optional, bypass cache and regenerate

    Returns:
    - personalized_bullets: List of 2-3 personalized prerequisite explanations
    - generated_at: Timestamp when primer was generated
    - from_cache: Whether result came from cache
    - stale: Whether cache was stale (returned anyway)
    - personalized_available: Whether personalization was possible
    """
    try:
        logger.info(
            f"Generating personalized primer | user_id={request.user_id} | "
            f"lesson_id={request.lesson_id} | force_refresh={request.force_refresh}"
        )

        # Validate lesson exists
        lesson = lesson_crud.get(db, request.lesson_id)
        if not lesson:
            logger.warning(f"Lesson not found | lesson_id={request.lesson_id}")
            raise HTTPException(status_code=404, detail="Lesson not found")

        service = PrimerService(db)
        result = await service.generate_personalized_primer(
            user_id=request.user_id,
            lesson_id=request.lesson_id,
            force_refresh=request.force_refresh
        )

        logger.info(
            f"Personalized primer generated | user_id={request.user_id} | "
            f"lesson_id={request.lesson_id} | from_cache={result.get('from_cache')} | "
            f"personalized_available={result.get('personalized_available')}"
        )

        return PersonalizedPrimerResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating personalized primer | user_id={request.user_id} | "
            f"lesson_id={request.lesson_id} | error={str(e)}"
        )
        traceback.print_exc()

        # Return fallback response instead of 500 error
        return PersonalizedPrimerResponse(
            personalized_bullets=[],
            generated_at=None,
            from_cache=False,
            stale=False,
            personalized_available=False
        )


@primers_router.post("/personalized/stream")
async def stream_personalized_primer(
    request: PersonalizedPrimerRequest,
    db: Session = Depends(get_db)
):
    """
    Stream personalized primer generation in real-time.

    This endpoint returns Server-Sent Events (SSE) with the following event types:
    - status: Status updates (checking cache, generating, etc.)
    - llm_chunk: Raw LLM tokens as they're generated (real-time streaming)
    - bullet: Individual parsed bullet after LLM completes
    - metadata: Final metadata (from_cache, personalized_available, etc.)
    - error: Error information
    - done: Completion signal

    Example SSE format:
    event: status
    data: {"message": "Checking cache..."}

    event: llm_chunk
    data: {"content": "{\n  \"person"}

    event: bullet
    data: {"index": 0, "content": "First personalized bullet..."}

    event: done
    data: {"success": true}
    """

    async def event_generator():
        """Generate SSE events for streaming primer generation"""
        try:
            logger.info(
                f"Starting streaming primer generation | user_id={request.user_id} | "
                f"lesson_id={request.lesson_id} | force_refresh={request.force_refresh}"
            )

            # Send initial status
            yield f"event: status\ndata: {json.dumps({'message': 'Starting primer generation...'})}\n\n"

            # Validate lesson exists
            lesson = lesson_crud.get(db, request.lesson_id)
            if not lesson:
                logger.warning(f"Lesson not found | lesson_id={request.lesson_id}")
                yield f"event: error\ndata: {json.dumps({'error': 'Lesson not found'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'success': False})}\n\n"
                return

            service = PrimerService(db)

            # Stream the generation process
            async for event in service.stream_personalized_primer(
                user_id=request.user_id,
                lesson_id=request.lesson_id,
                force_refresh=request.force_refresh
            ):
                event_type = event.get("type", "status")
                event_data = {k: v for k, v in event.items() if k != "type"}

                # Format as SSE
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

            # Send completion event
            yield f"event: done\ndata: {json.dumps({'success': True})}\n\n"

            logger.info(
                f"Streaming primer generation completed | user_id={request.user_id} | "
                f"lesson_id={request.lesson_id}"
            )

        except HTTPException as http_exc:
            logger.error(f"HTTP error in streaming | error={str(http_exc)}")
            yield f"event: error\ndata: {json.dumps({'error': str(http_exc.detail)})}\n\n"
            yield f"event: done\ndata: {json.dumps({'success': False})}\n\n"

        except Exception as e:
            logger.error(
                f"Error in streaming primer generation | user_id={request.user_id} | "
                f"lesson_id={request.lesson_id} | error={str(e)}"
            )
            traceback.print_exc()

            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': 'Internal server error', 'personalized_available': False})}\n\n"
            yield f"event: done\ndata: {json.dumps({'success': False})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )
