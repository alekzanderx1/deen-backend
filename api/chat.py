from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest
from core import pipeline
from core.memory import make_history
import traceback

chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@chat_router.post("/")
async def chat_pipeline_ep(request: ChatRequest):
    """
    Non-streaming chat endpoint with Redis-backed memory.
    Expects:
      {
        "user_query": "What does Islam say about justice?",
        "session_id": "user42:thread-7"
      }
    """
    user_query = (request.user_query or "").strip()
    session_id = (getattr(request, "session_id", "") or "").strip()

    if not user_query:
        return {"response": "Please provide an appropriate query."}
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    try:
        ai_response = pipeline.chat_pipeline(user_query, session_id)
        return {"response": ai_response}
    except Exception:
        # Log the exception elsewhere; don't leak details to client
        raise HTTPException(status_code=500, detail="Internal Server Error")


@chat_router.post("/stream")
async def chat_pipeline_stream_ep(request: ChatRequest):
    """
    Streaming chat endpoint with Redis-backed memory.
    Expects:
      {
        "user_query": "What does Islam say about justice?",
        "session_id": "user42:thread-7",
        "language": "english"
      }
    """
    user_query = (request.user_query or "").strip()
    session_id = (getattr(request, "session_id", "") or "").strip()
    target_language = (getattr(request, "language", "") or "english").strip()

    if not user_query:
        raise HTTPException(status_code=400, detail="Please provide an appropriate query.")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    try:
        # Returns a StreamingResponse from the pipeline
        return pipeline.chat_pipeline_streaming(user_query, session_id, target_language)
    except Exception as e:
        # Log internally; keep response generic
        print("UNHANDLED ERROR in /chat/stream:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# OPTIONAL: Clear a conversation's memory (useful for a "Reset chat" button)
@chat_router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    try:
        history = make_history(session_id)
        history.clear()
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to clear session")