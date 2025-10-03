import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DEEN_DENSE_INDEX_NAME = os.getenv("DEEN_DENSE_INDEX_NAME")
DEEN_SPARSE_INDEX_NAME = os.getenv("DEEN_SPARSE_INDEX_NAME")
DENSE_RESULT_WEIGHT = os.getenv("DENSE_RESULT_WEIGHT",0.8)
SPARSE_RESULT_WEIGHT = os.getenv("SPARSE_RESULT_WEIGHT",0.2)
REFERENCE_FETCH_COUNT = int(os.getenv("REFERENCE_FETCH_COUNT", 10))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "dev:chat")
TTL_SECONDS = int(os.getenv("REDIS_TTL_SECONDS", "12000"))  # default 30d
MAX_MESSAGES = int(os.getenv("REDIS_MAX_MESSAGES", "30"))
COGNITO_REGION = os.getenv("COGNITO_REGION")
COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID")

# Check if keys are loaded (optional)
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")

# Check if keys are loaded (optional)
if not DEEN_DENSE_INDEX_NAME or not DEEN_SPARSE_INDEX_NAME:
    raise ValueError("Missing Index names! Ensure they are set in the .env file.")