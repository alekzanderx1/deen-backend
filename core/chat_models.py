from langchain_anthropic import ChatAnthropic
from core.config import ANTHROPIC_API_KEY


def get_generator_model():
    """Returns ChatAnthropic for long-form generation (fiqh answers, general responses)."""
    from core.config import LARGE_LLM
    return ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=4096)


def get_enhancer_model():
    """Returns ChatAnthropic for query enhancement (short rewrites)."""
    from core.config import SMALL_LLM
    return ChatAnthropic(model=SMALL_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=512)


def get_classifier_model():
    """Returns ChatAnthropic for fiqh classification and SEA structured output."""
    from core.config import LARGE_LLM
    return ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=2048)


def get_translator_model():
    """Returns ChatAnthropic bound to temperature=0 for deterministic translation."""
    from core.config import LARGE_LLM
    base = ChatAnthropic(model=LARGE_LLM, api_key=ANTHROPIC_API_KEY, max_tokens=1024)
    return base.bind(temperature=0)
