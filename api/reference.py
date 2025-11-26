from fastapi import APIRouter, HTTPException, Query
from models.schemas import ReferenceRequest
from core import pipeline

ref_router = APIRouter(
    prefix='/references',
    tags=['references']
)

# Takes query parameter called 'sect', which can equal to sunni, shia, or both.
# Also accepts 'limit' parameter to control number of references (1-50, default: 10)
# Example usage: http://localhost:8000/references?sect=both&limit=20
# Example json body input:: {"user_query": "What does Islam say about justice?"}
@ref_router.post("/")
async def references_pipeline(
    request: ReferenceRequest, 
    sect: str = Query("both", enum=["sunni", "shia", "both"]),
    limit: int = Query(10, ge=1, le=50, description="Number of references to fetch (1-50)")
):
    user_query = request.user_query.strip()

    if not user_query:
        raise HTTPException(status_code=400, detail="Please provide an appropriate query.")
    
    try:
        results = pipeline.references_pipeline(user_query, sect, limit)
        return {"response": results}
        
    except Exception as e:
        print(f"{str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")