from modules.classification import classifier
from modules.embedding import embedder
from modules.enhancement import enhancer
from modules.generation import generator, stream_generator
from modules.retrieval import retriever
from fastapi.responses import StreamingResponse
from modules.translation import translator
from core import utils
from itertools import chain
from core.config import REFERENCE_FETCH_COUNT
import json

# Not updated for memory persistence yet
def chat_pipeline(user_query: str, session_id: str):
    # # Step 1: Classify query (fiqh or non-fiqh)
    is_non_islamic = classifier.classify_non_islamic_query(user_query)
    if is_non_islamic:
        return "This question is not related to the domain of Islamic education. Please ask relevant questions."
    

    # # Step 2: Classify query (fiqh or non-fiqh)
    is_fiqh = classifier.classify_fiqh_query(user_query)
    
    if is_fiqh:
        return "This is a fiqh-related question. Please consult a qualified scholar."
    
    # Step 3: Enhance query
    enhanced_query = enhancer.enhance_query(user_query)

    # Step 4: Retrieve relevant documents from Pinecone
    relevant_docs = retriever.retrieve_documents(enhanced_query,REFERENCE_FETCH_COUNT)

    # Step 5: Generate AI response using OpenAI
    ai_response = generator.generate_response(enhanced_query, relevant_docs)

    return ai_response


# Updated for in-chat memory persistence
def chat_pipeline_streaming(user_query: str, session_id: str, target_language: str = "english"):
    

    # Step 1: Translate user query from target language to english (if needed)
    tl = (target_language or "english").strip().lower()
    if tl != "english":
        try:
            user_query = translator.translate_to_english(user_query, tl)
        except Exception as e:
            # Log the error but don’t break the pipeline
            print(f"[chat_pipeline_streaming] Translation failed: {e}")
            # Fallback: keep the original user_query

    # Step 2: Classify the query
    is_non_islamic = classifier.classify_non_islamic_query(user_query)
    if is_non_islamic:
        message = "This question is not related to the domain of Islamic education. Please ask relevant questions."
        return StreamingResponse(utils.stream_message(message), media_type="text/event-stream")

    is_fiqh = classifier.classify_fiqh_query(user_query)
    if is_fiqh:
        message = "This is a fiqh-related question. Please consult a qualified scholar."
        return StreamingResponse(utils.stream_message(message), media_type="text/event-stream")

    # Step 3: Enhance the query
    enhanced_query = enhancer.enhance_query(user_query)

    # Step 4: Retrieve relevant documents from Pinecone
    # relevant_docs = retriever.retrieve_documents(enhanced_query, 5) # NOTE: Changed to 5 references for chatbot
    relevant_shia_docs = retriever.retrieve_shia_documents(enhanced_query, 4)
    relevant_sunni_docs = retriever.retrieve_sunni_documents(enhanced_query, 2)

    all_relevant_docs = relevant_shia_docs + relevant_sunni_docs

    # Step 5: Stream the AI response from OpenAI
    response_generator = stream_generator.generate_response_stream(user_query, all_relevant_docs, session_id, target_language=tl)

    #Step 6: Stream the formatted references in JSON format
    references_tail = utils.stream_message('\n\n\n[REFERENCES]\n\n\n' + json.dumps(utils.format_references_as_json(all_relevant_docs)))

    # Return a StreamingResponse with appropriate media type.
    return StreamingResponse(chain(response_generator, references_tail), media_type="text/event-stream")



def references_pipeline(user_query: str, sect: str):
    # # Step 1: Classify query (fiqh or non-fiqh)
    is_non_islamic = classifier.classify_non_islamic_query(user_query)
    if is_non_islamic:
        return "This question is not related to the domain of Islamic education. Please ask relevant questions."
    
    # Step 2: Enhance query
    enhanced_query = enhancer.enhance_query(user_query)

    # Step 3: Retrieve relevant documents from Pinecone
    results = {}
    if sect in ["shia", "both"]:
        results["shia"] = utils.format_references_as_json(retriever.retrieve_shia_documents(enhanced_query,REFERENCE_FETCH_COUNT))
    if sect in ["sunni", "both"]:
        results["sunni"] = utils.format_references_as_json(retriever.retrieve_sunni_documents(enhanced_query,REFERENCE_FETCH_COUNT))

    return results