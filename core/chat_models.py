from core.config import OPENAI_API_KEY
from langchain.chat_models import init_chat_model

# Models
# gpt-4o
# gpt-5-mini-2025-08-07
def get_generator_model():
    """
    Initializes and returns the chat model.
    """
    print("INSIDE get_generator_model")
    
    try:
        from core.config import LARGE_LLM
        chat_model = init_chat_model(
            model=LARGE_LLM,
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
        from core.config import SMALL_LLM
        chat_model = init_chat_model(
            model=SMALL_LLM,
            openai_api_key=OPENAI_API_KEY
        )
        return chat_model
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise e
    

def get_classifier_model():
    """
    Initializes and returns the chat model.
    """
    print("INSIDE get_classifier_model")
    
    try:
        from core.config import SMALL_LLM
        chat_model = init_chat_model(
            model=SMALL_LLM,
            openai_api_key=OPENAI_API_KEY
        )
        return chat_model
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        raise e
    

def get_translator_model():
    print("INSIDE get_translator_model")
    try:
        from core.config import SMALL_LLM
        base = init_chat_model(
            model=SMALL_LLM,
            openai_api_key=OPENAI_API_KEY,
        )
        return base.bind(temperature=0)
    except Exception as e:
        print(f"Error initializing translator LLM: {e}")
        raise e