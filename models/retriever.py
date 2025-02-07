from pinecone import Pinecone, ServerlessSpec
from config import PINECONE_API_KEY

# Initialize a client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Connect to your index
index = pc.Index(host="https://deen-index-1-lscg4rr.svc.aped-4627-b74a.pinecone.io")

def retrieve_documents(query_embedding):
    print("INSIDE retrieve_documents")
    results = index.query(
        namespace="ns1",
        vector=query_embedding,
        top_k=7,
        include_values=False,
        include_metadata=True
    )
    print("Documents retrieved. Example:", results["matches"][0]["metadata"])
    return [match["metadata"] for match in results["matches"]]

"""
Returns a list of the following:
'metadata': {'book': '4 | The Book about people with Divine Authority',
              'chapter': 'Chapter 93 | The Birth of the Imams',
              'hadith_number': '5',
              'text': 'Al-Husayn ibn Muhammad has narrated from Mu‘alla ibn Muhammad from Ahmad ibn Muhammad ibn ‘Abd...',
              'author': 'Shaykh Muḥammad b. Yaʿqūb al-Kulaynī',
              'volume': 'NA',
              'source': 'Volume 1'
              }
"""