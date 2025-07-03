from core.config import  DEEN_INDEX_NAME, DEEN_SUNNI_INDEX_NAME
import core.vectorstore as vectorstore_module
import traceback

def retrieve_documents(query_embedding):
    print("INSIDE retrive_documents")
    try:
        vectorstore = vectorstore_module._get_vectorstore(DEEN_INDEX_NAME)
        docs = vectorstore.search(query_embedding,'similarity',k=7)
        return docs
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        traceback.print_exc()
        return []

def retrieve_shia_documents(query_embedding):
    print("INSIDE shia retrive_documents")
    try:
        vectorstore = vectorstore_module._get_vectorstore(DEEN_INDEX_NAME)
        docs = vectorstore.search(query_embedding,'similarity',k=7)
        return docs
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        traceback.print_exc()
        return []

def retrieve_sunni_documents(query_embedding):
    print("INSIDE sunni retrive_documents")
    try:
        vectorstore = vectorstore_module._get_vectorstore(DEEN_SUNNI_INDEX_NAME)
        docs = vectorstore.search(query_embedding,'similarity',k=7)
        return docs
    except Exception as e:
        print(f"Error retrieving documents: {e}")
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