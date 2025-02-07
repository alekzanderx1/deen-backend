import torch
from sentence_transformers import SentenceTransformer

device = torch.device("mps") if torch.backends.mps.is_available() else "cpu"

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
model.to(device)


def generate_embedding(query: str):
    print("INSIDE generate_embedding")
    embedding = model.encode(query).tolist()
    # print("embedding generated:", embedding)
    return embedding