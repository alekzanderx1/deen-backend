from openai import OpenAI
from core.config import OPENAI_API_KEY
from core import utils
from core import chat_models
from core import prompt_templates
from core.memory import with_redis_history, trim_history, make_history

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