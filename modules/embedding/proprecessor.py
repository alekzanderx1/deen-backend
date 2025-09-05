import string
from core import constants


def normalize_text(text: str) -> str:
    # Lowercase
    text = text.lower()

    # Remove punctuation
    text = text.translate(str.maketrans("", "", string.punctuation))

    # Normalize Islamic terms
    words = text.split()
    normalized_words = [constants.ISLAMIC_TERMS_MAP.get(word, word) for word in words]

    return " ".join(normalized_words)