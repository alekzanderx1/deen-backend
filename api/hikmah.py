from fastapi import APIRouter, HTTPException
from models.schemas import ElaborationRequest
from core import pipeline
import traceback

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
