from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models.query_classifier import classify_fiqh_query, classify_non_islamic_query
from models.query_enhancer import enhance_query
from models.embedding import generate_embedding
from models.retriever import retrieve_documents
from models.response_generator import generate_response

app = FastAPI()

# Define request model
class ChatRequest(BaseModel):
    user_query: str

@app.get("/")
def home():
    return {"message": "Welcome to the Shia Islam Chat API"}

# Define the Chat Pipeline API
@app.post("/chat/")
async def chat_pipeline(request: ChatRequest):
    user_query = request.user_query  # Extract the query from JSON request
    print(f"user_query: {user_query}")

    if not user_query or user_query.strip() == "":
        return {"response": "Please provide an appropriate query."}
    
    try:
        # # Step 1: Classify query (fiqh or non-fiqh)
        is_non_islamic = classify_non_islamic_query(user_query)
        if is_non_islamic:
            return {"response": "This question is not related to the domain of Islamic education. Please ask relevant questions."}
        

        # # Step 2: Classify query (fiqh or non-fiqh)
        is_fiqh = classify_fiqh_query(user_query)
        
        if is_fiqh:
            return {"response": "This is a fiqh-related question. Please consult a qualified scholar."}
        
        # Step 3: Enhance query
        enhanced_query = enhance_query(user_query)

        # Step 4: Generate embedding
        query_embedding = generate_embedding(enhanced_query)

        # Step 5: Retrieve relevant documents from Pinecone
        relevant_docs = retrieve_documents(query_embedding)

        # Step 6: Generate AI response using OpenAI
        ai_response = generate_response(enhanced_query, relevant_docs)

        return {"response": ai_response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")