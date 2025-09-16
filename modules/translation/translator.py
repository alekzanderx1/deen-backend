from core import chat_models
from core import prompt_templates

def translate_to_english(text: str, source_language: str | None = None) -> str:
    """
    Translate `text` from `source_language` to English using a LangChain chat model.
    Returns the original `text` on error.
    """
    if not text:
        return ""

    if (source_language or "").strip().lower() == "english":
        return text

    try:
        chat_model = chat_models.get_translator_model()
        prompt = prompt_templates.translation_prompt_template.invoke({"source_language": source_language or "unknown", "text": text})
        response = chat_model.invoke(prompt.to_messages())
        out = (getattr(response, "content", None) or "").strip()
        return out or text
    except Exception as e:
        print(f"[translate_to_english] error: {e}")
        return text