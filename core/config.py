import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DEEN_INDEX_LINK = os.getenv("DEEN_INDEX_LINK")
DEEN_SUNNI_INDEX_LINK = os.getenv("DEEN_SUNNI_INDEX_LINK")

# Check if keys are loaded (optional)
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")