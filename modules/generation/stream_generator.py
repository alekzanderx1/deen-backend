from openai import OpenAI
from core.config import OPENAI_API_KEY
from core import utils
from core import chat_models
from core import prompt_templates
from core.memory import with_redis_history, trim_history, make_history
import asyncio
from typing import Optional
import threading

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_response_stream(query: str, retrieved_docs: list, session_id: str, target_language: str = "english"):
    """
    Generates a streaming response using the chat model.
    Yields chunks of text as they are generated.
    """
    print("INSIDE generate_response_stream")
    # Format retrieved references
    references = utils.compact_format_references(retrieved_docs=retrieved_docs)

    chat_model = chat_models.get_generator_model()

    # prompt = prompt_templates.generator_prompt_template.invoke({"query":query,"references":references})
    prompt = prompt_templates.generator_prompt_template
    chain = prompt | chat_model

    chain_with_history = with_redis_history(chain)

    # Stream chunks to caller
    for chunk in chain_with_history.stream(
        {"target_language": target_language, "query": query, "references": references},
        config={"configurable": {"session_id": session_id}},
    ):
        # `chunk` is typically an AIMessageChunk or string
        yield getattr(chunk, "content", str(chunk) if chunk is not None else "")

    # After stream completes, cap history length
    hist = make_history(session_id)
    trim_history(hist)

def generate_elaboration_response_stream(selected_text: str, context_text: str, hikmah_tree_name: str, lesson_name: str, lesson_summary: str, retrieved_docs: list, user_id: Optional[str] = None):
    """
    Generates a streaming response using the chat model.
    Yields chunks of text as they are generated.
    If user_id is provided, triggers memory agent after streaming completes.
    """
    print("INSIDE generate_elaboration_response_stream")
    # Format retrieved references
    references = utils.compact_format_references(retrieved_docs=retrieved_docs)

    chat_model = chat_models.get_generator_model()

    prompt = prompt_templates.hikmah_elaboration_prompt_template
    chain = prompt | chat_model

    # Capture AI response for memory agent (if user_id provided)
    ai_response_chunks = []

    # Stream chunks to caller
    for chunk in chain.stream(
        {"selected_text": selected_text, "context_text": context_text, "hikmah_tree_name": hikmah_tree_name, "lesson_name": lesson_name, "lesson_summary": lesson_summary, "references": references}):
        # `chunk` is typically an AIMessageChunk or string
        content = getattr(chunk, "content", str(chunk) if chunk is not None else "")
        
        # Capture for memory agent
        if user_id:
            ai_response_chunks.append(content)
        
        yield content
    
    # After streaming completes, trigger memory agent if user_id provided
    if user_id:
        # Fire and forget: Run memory update in separate thread
        # Note: We don't pass ai_response or full context_text to avoid overwhelming the agent
        # The selected_text + lesson/tree name is the key signal
        thread = threading.Thread(
            target=_run_memory_update_sync,
            args=(user_id, selected_text, hikmah_tree_name, lesson_name),
            daemon=True  # Daemon thread won't prevent shutdown
        )
        thread.start()
        print(f"🧠 Memory agent thread started for user {user_id}")


def _run_memory_update_sync(user_id: str, selected_text: str,
                            hikmah_tree_name: str, lesson_name: str):
    """
    Synchronous wrapper to run async memory update in a separate thread.
    This is a true "fire and forget" background task that runs independently
    of the API response thread.
    
    Note: We only pass essential context (selected_text, lesson, tree) to avoid
    overwhelming the memory agent with verbose data.
    """
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async memory update
        loop.run_until_complete(_update_hikmah_memory(
            user_id=user_id,
            selected_text=selected_text,
            hikmah_tree_name=hikmah_tree_name,
            lesson_name=lesson_name
        ))
        
        loop.close()
        
    except Exception as e:
        print(f"❌ Error in hikmah memory update background thread: {e}")
        import traceback
        traceback.print_exc()


async def _update_hikmah_memory(user_id: str, selected_text: str,
                                hikmah_tree_name: str, lesson_name: str):
    """
    Background task to update user memory after hikmah elaboration.
    Runs in a separate thread with its own event loop.
    Thread-safe and handles multiple concurrent users.
    
    Only receives essential context:
    - selected_text: What the user asked about (the key signal)
    - lesson_name: Which lesson they're in
    - hikmah_tree_name: Which educational tree they're studying
    
    This focused approach helps the agent make precise, non-redundant notes.
    """
    db = None
    try:
        from agents.models.db_config import SessionLocal
        from agents.core.universal_memory_agent import UniversalMemoryAgent
        
        # Create a fresh database session for this background thread
        # Important: Create session inside try block to ensure proper cleanup
        db = SessionLocal()
        
        # Initialize memory agent with the fresh session
        memory_agent = UniversalMemoryAgent(db)
        
        # Analyze hikmah elaboration interaction with optimized context
        result = await memory_agent.analyze_hikmah_elaboration(
            user_id=user_id,
            selected_text=selected_text,
            hikmah_tree_name=hikmah_tree_name,
            lesson_name=lesson_name
            # Note: context_text removed - it's too verbose and not needed
        )
        
        # Log success with details
        print(f"✅ Hikmah memory updated for user {user_id}")
        if result.get('notes_added'):
            print(f"   📝 Added {len(result['notes_added'])} note(s)")
        
    except Exception as e:
        print(f"❌ Error updating hikmah memory for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Always close the database session, even if there's an error
        if db is not None:
            try:
                db.close()
            except Exception as close_error:
                print(f"⚠️ Error closing DB session: {close_error}")