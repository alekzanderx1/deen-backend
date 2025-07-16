from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import ChatRequest
from core import utils, pipeline

chat_router = APIRouter(
    prefix='/chat',
    tags=['chat']
)

@chat_router.post("/")
async def chat_pipeline(request: ChatRequest):
    user_query = request.user_query  # Extract the query from JSON request
    print(f"user_query: {user_query}")

    if not user_query or user_query.strip() == "":
        return {"response": "Please provide an appropriate query."}
    
    try:
        ai_response = pipeline.chat_pipeline(user_query)
        return {"response": ai_response}

    except Exception as e:
        # TODO: Move the exception message to log files, don't show the error to user or in API response
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    


# Example json body input: {"user_query": "What does Islam say about justice?"}
@chat_router.post("/stream")
async def chat_pipeline_stream(request: ChatRequest):
    user_query = request.user_query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Please provide an appropriate query.")

    try:
        return pipeline.chat_pipeline_streaming(user_query)
    except Exception as e:
        # TODO: Move the exception message to log files, don't show the error to user or in API response
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")