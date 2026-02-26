from core.config import DEEN_SPARSE_INDEX_NAME, DEEN_DENSE_INDEX_NAME, QURAN_DENSE_INDEX_NAME
import core.vectorstore as vectorstore_module
from modules.reranking import reranker
from modules.embedding import embedder
from core.utils import decompress_text
import traceback


def retrieve_documents(query,no_of_docs=10):
    print("INSIDE retrive_documents")
    try:
        dense_vectorstore = vectorstore_module._get_vectorstore(DEEN_DENSE_INDEX_NAME)
        dense_docs_and_score = dense_vectorstore.similarity_search_with_score(query,k=20)

        sparse_embedding = embedder.generate_sparse_embedding(query)
        spare_vectorstore = vectorstore_module._get_sparse_vectorstore(DEEN_SPARSE_INDEX_NAME)
        sparse_docs = spare_vectorstore.query(
                top_k=20,
                include_metadata=True,
                sparse_vector=sparse_embedding,
                namespace="ns1"
        )

        result = reranker.rerank_documents(dense_docs_and_score, sparse_docs,no_of_docs)
        return result
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        traceback.print_exc()
        return []

def retrieve_shia_documents(query,no_of_docs=10):
    print("INSIDE shia retrive_documents")
    try:
        dense_vectorstore = vectorstore_module._get_vectorstore(DEEN_DENSE_INDEX_NAME)
        dense_docs_and_score = dense_vectorstore.similarity_search_with_score(query,filter={'sect':'shia'},k=no_of_docs)

        sparse_embedding = embedder.generate_sparse_embedding(query)
        spare_vectorstore = vectorstore_module._get_sparse_vectorstore(DEEN_SPARSE_INDEX_NAME)
        sparse_docs = spare_vectorstore.query(
                top_k=no_of_docs,
                include_metadata=True,
                sparse_vector=sparse_embedding,
                namespace="ns1",
                filter={'sect':'shia'}
        )

        result = reranker.rerank_documents(dense_docs_and_score, sparse_docs,no_of_docs)
        return result
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        traceback.print_exc()
        return []

def retrieve_sunni_documents(query,no_of_docs=10):
    print("INSIDE sunni retrive_documents")
    try:
        dense_vectorstore = vectorstore_module._get_vectorstore(DEEN_DENSE_INDEX_NAME)
        dense_docs_and_score = dense_vectorstore.similarity_search_with_score(query,filter={'sect':'sunni'},k=no_of_docs)

        sparse_embedding = embedder.generate_sparse_embedding(query)
        spare_vectorstore = vectorstore_module._get_sparse_vectorstore(DEEN_SPARSE_INDEX_NAME)
        sparse_docs = spare_vectorstore.query(
                top_k=no_of_docs,
                include_metadata=True,
                sparse_vector=sparse_embedding,
                namespace="ns1",
                filter={'sect':'sunni'}
        )

        result = reranker.rerank_documents(dense_docs_and_score, sparse_docs, no_of_docs)
        return result
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        traceback.print_exc()
        return []


def retrieve_quran_documents(query, no_of_docs=5):
    """
    Retrieve Quran Tafsir documents from the dedicated dense-only Pinecone index.
    Uses direct Pinecone query (no sparse search, no reranking).
    """
    print("INSIDE quran retrieve_documents")
    try:
        query_vector = embedder.getDenseEmbedder().embed_query(query)

        index = vectorstore_module._get_sparse_vectorstore(QURAN_DENSE_INDEX_NAME)
        results = index.query(
            vector=query_vector,
            top_k=no_of_docs,
            include_metadata=True,
            namespace="ns1"
        )

        docs = []
        for match in results.matches:
            md = match.metadata or {}
            text_chunk = decompress_text(md.get("text_chunk", ""))
            quran_translation = decompress_text(md.get("english_quran_translation", ""))
            docs.append({
                "chunk_id": match.id,
                "metadata": md,
                "page_content_en": text_chunk,
                "quran_translation": quran_translation
            })
        return docs
    except Exception as e:
        print(f"Error retrieving Quran documents: {e}")
        traceback.print_exc()
        return []


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