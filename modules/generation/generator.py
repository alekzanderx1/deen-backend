from core.config import OPENAI_API_KEY
from core import utils
from core import chat_models
from core import prompt_templates

def generate_response(query: str, retrieved_docs: list):
    """
    Generates AI response using chat model.
    This function takes a user query and a list of retrieved documents,
    """
    print("INSIDE generate_response")

    # Format retrieved references
    references = utils.format_references(retrieved_docs)

    chat_model = chat_models.get_generator_model()

    prompt = prompt_templates.generator_prompt_template.invoke({"query":query,"references":references})

    response = chat_model.invoke(prompt.to_messages())

    return response.content.strip()