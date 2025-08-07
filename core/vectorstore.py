from core.config import PINECONE_API_KEY
from langchain_pinecone import PineconeVectorStore
from modules.embedding import embedder
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(
        api_key=PINECONE_API_KEY
    )

def _get_sparse_vectorstore(index_name):
    index = pc.Index(index_name)
    return index


def _get_vectorstore(index_name):
    embeddings = embedder.getDenseEmbedder()
    try:
        return PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            pinecone_api_key=PINECONE_API_KEY,
            namespace="ns1",
            text_key="text_en"
        )
    except Exception as e:
        print(f"Error initializing PineconeVectorStore: {e}")
        raise e