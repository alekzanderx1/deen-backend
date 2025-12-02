from core.config import OPENAI_API_KEY
from core import chat_models
from core import prompt_templates
from typing import Optional
from core.memory import make_history


def enhance_query(query: str, session_id: Optional[str] = None) -> str:
    """
    Enhances user query by adding more context to improve retrieval.
    If session_id is provided, the recent chat history from Redis is injected
    into the prompt via the "chat_history" MessagesPlaceholder.
    """
    print("INSIDE enhance_query")

    chat_model = chat_models.get_enhancer_model()

    # Load history if session provided
    history_messages = []
    if session_id:
        try:
            history = make_history(session_id)
            history_messages = history.messages
        except Exception as e:
            print(f"[enhance_query] failed loading history: {e}")
            history_messages = []

    # Always invoke with chat_history (empty list if not available)
    prompt = prompt_templates.enhancer_prompt_template.invoke(
        {"text": query, "chat_history": history_messages}
    )
    response = chat_model.invoke(prompt.to_messages())

    print("Generated enhanced query:", response.content)
    return response.content.strip()


def enhance_elaboration_query(selected_text: str, context_text: str, hikmah_tree_name: str, lesson_name: str, lesson_summary: str) -> str:
    """
    Enhances user query by adding more context to improve retrieval.
    """
    print("INSIDE enhance_query")

    chat_model = chat_models.get_enhancer_model()

    prompt = prompt_templates.elaboration_enhancer_prompt_template.invoke({"selected_text":selected_text, "context_text":context_text, "hikmah_tree_name":hikmah_tree_name, "lesson_name":lesson_name, "lesson_summary":lesson_summary})

    response = chat_model.invoke(prompt.to_messages())

    print("Generated enhanced query:", response.content)

    return response.content.strip()