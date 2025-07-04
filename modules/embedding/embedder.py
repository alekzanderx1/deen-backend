import torch
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings

device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
model.to(device)

def getEmbedder():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

def generate_embedding(query: str):
    print("INSIDE generate_embedding")
    embedding = model.encode(query).tolist()
    return embedding