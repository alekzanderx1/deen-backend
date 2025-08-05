import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DEEN_DENSE_INDEX_NAME = os.getenv("DEEN_DENSE_INDEX_NAME")
DEEN_SPARSE_INDEX_NAME = os.getenv("DEEN_SPARSE_INDEX_NAME")
DENSE_RESULT_WEIGHT = os.getenv("DENSE_RESULT_WEIGHT",0.7)
SPARSE_RESULT_WEIGHT = os.getenv("SPARSE_RESULT_WEIGHT",0.3)
REFERENCE_FETCH_COUNT = int(os.getenv("REFERENCE_FETCH_COUNT", 10))

# Check if keys are loaded (optional)
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")

# Check if keys are loaded (optional)
if not DEEN_DENSE_INDEX_NAME or not DEEN_SPARSE_INDEX_NAME:
    raise ValueError("Missing Index names! Ensure they are set in the .env file.")