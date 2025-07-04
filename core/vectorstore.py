from core.config import PINECONE_API_KEY
from langchain_pinecone import PineconeVectorStore
from modules.embedding import embedder

def _get_vectorstore(index_link):
    embeddings = embedder.getEmbedder()
    try:
        return PineconeVectorStore(
            index_name=index_link,
            embedding=embeddings,
            pinecone_api_key=PINECONE_API_KEY,
            namespace="ns1"
        )
    except Exception as e:
        print(f"Error initializing PineconeVectorStore: {e}")
        raise e