from core.config import OPENAI_API_KEY
from core import chat_models
from core import prompt_templates

def enhance_query(query: str) -> str:
    """
    Enhances user query by adding more context to improve retrieval.
    """
    print("INSIDE enhance_query")

    chat_model = chat_models.get_enhancer_model()

    prompt = prompt_templates.enhancer_prompt_template.invoke({"text":query})

    response = chat_model.invoke(prompt.to_messages())

    print("Generated enhanced query:", response.content)

    return response.content.strip()