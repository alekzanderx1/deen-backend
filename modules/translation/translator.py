# modules/translation/translator.py
from core import chat_models
from langchain.prompts import ChatPromptTemplate

_SYSTEM_PROMPT = """You are a precise, faithful translator.
- Translate the user's text into English.
- Preserve religious names/terms (e.g., Qur'an, hadith, Imam names) accurately.
- Keep quotes as quotes; do not add commentary or citations.
- Output ONLY the English translation—no explanations, no notes, no markup."""

# Build a tiny prompt locally (keeps changes minimal)
_translation_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("user", "Source language: {source_language}\n\nText:\n{text}")
])

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
        model = chat_models.get_translator_model()
        prompt = _translation_prompt.invoke({
            "source_language": source_language or "unknown",
            "text": text,
        })
        resp = model.invoke(prompt.to_messages())
        out = (getattr(resp, "content", None) or "").strip()
        return out or text
    except Exception as e:
        print(f"[translate_to_english] error: {e}")
        return text