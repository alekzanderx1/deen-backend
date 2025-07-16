from core.config import OPENAI_API_KEY
from langchain.chat_models import init_chat_model

def get_generator_model():
    """
    Initializes and returns the chat model.
    """
    print("INSIDE get_generator_model")
    
    try:
        chat_model = init_chat_model(
            model="gpt-4o",
            openai_api_key=OPENAI_API_KEY
        )
        return chat_model
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise e
    

def get_enhancer_model():
    """
    Initializes and returns the chat model.
    """
    print("INSIDE get_enhancer_model")
    
    try:
        chat_model = init_chat_model(
            model="gpt-4o-mini",
            openai_api_key=OPENAI_API_KEY
        )
        return chat_model
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise e