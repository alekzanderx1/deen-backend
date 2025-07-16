from openai import OpenAI
from core.config import OPENAI_API_KEY
from core import utils
from core import chat_models
from core import prompt_templates

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_response_stream(query: str, retrieved_docs: list):
    """
    Generates a streaming response using the chat model.
    Yields chunks of text as they are generated.
    """
    print("INSIDE generate_response_stream")
    # Format retrieved references
    references = utils.format_references(retrieved_docs)

    chat_model = chat_models.get_generator_model()

    prompt = prompt_templates.generator_prompt_template.invoke({"query":query,"references":references})

    response = chat_model.stream(prompt.to_messages())

    for chunk in response:
        yield chunk.content