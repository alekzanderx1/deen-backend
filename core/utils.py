from langchain_core.documents import Document
import traceback
import base64
import gzip

def format_references(retrieved_docs: list) -> str:
    """
    Formats retrieved hadiths and Quranic references for better readability.
    """
    print("INSIDE format_references")
    formatted_references = "\n\n**Retrieved References:**\n"

    try:
        if not retrieved_docs:
            return formatted_references + "\n(No relevant references were found in the database.)"

        for doc in retrieved_docs:
            author = doc['metadata'].get("author", "N/A")
            volume = doc['metadata'].get("volume", "N/A")
            book_number = doc['metadata'].get("book_number", "N/A")
            book_title = doc['metadata'].get("book_title", "N/A")
            chapter_number =  doc['metadata'].get("chapter_number", "N/A")
            chapter_title = doc['metadata'].get("chapter_title", "N/A")
            collection = doc['metadata'].get("collection", "N/A")             
            hadith_no = doc['metadata'].get("hadith_no", "N/A")
            text = doc['page_content_en'].strip() if doc['page_content_en'] else "No text available"

            formatted_references += (
                f"\n--------------------------------------\n"
                f"- **Book Title:** {book_title}\n"
                f"- **Author:** {author}\n"
                f"- **Volume:** {volume}\n"
                f"- **Book Number:** {book_number}\n"
                f"- **Chapter Title:** {chapter_title}\n"
                f"- **Collection:** {collection}\n"
                f"- **Hadith Number:** {hadith_no}\n"
                f"- **Chapter Number:** {chapter_number}\n"
                f"- **Text:** \"{text}\"\n"
                "---------------------------------------------"
            )
    except Exception as e:
        print(f"Error formatting references: {e}")
        traceback.print_exc()
        formatted_references += "\n\n**Error formatting references. Please check the data structure.**"

    return formatted_references

def format_references_as_json(retrieved_docs: list):
    """
    Formats retrieved hadiths and Quranic references into JSON format
    """
    print("INSIDE format_references_as_json")
    result = {"references": []}
    formatted_references = []
    try:
        if not retrieved_docs:
            return result

        for doc in retrieved_docs:
            reference = {
                "author": doc['metadata'].get("author", "N/A"),
                "volume": doc['metadata'].get("volume", "N/A"),
                "book_number": doc['metadata'].get("book_number", "N/A"),
                "book_title": doc['metadata'].get("book_title", "N/A"),
                "chapter_number": doc['metadata'].get("chapter_number", "N/A"),
                "chapter_title": doc['metadata'].get("chapter_title", "N/A"),
                "collection": doc['metadata'].get("collection", "N/A"),
                "grade_ar": doc['metadata'].get("grade_ar", "N/A"),
                "grade_en": doc['metadata'].get("grade_en", "N/A"),                
                "hadith_id": doc['metadata'].get("hadith_id", "N/A"),
                "hadith_no": doc['metadata'].get("hadith_no", "N/A"),
                "hadith_url": doc['metadata'].get("hadith_url", "N/A"),
                "lang": doc['metadata'].get("lang", "N/A"),
                "sect": doc['metadata'].get("sect", "N/A"),
                "reference": doc['metadata'].get("reference", "N/A"),
                "text": doc['page_content_en'].strip() if doc['page_content_en'] else "No text available",
                "text_ar": doc['page_content_ar'].strip() if doc['page_content_ar'] else "No Arabic text available"
            }
            formatted_references.append(reference)
    except Exception as e:
        print(f"Error formatting references: {e}")
        traceback.print_exc()
        return result
    
    result["references"] = formatted_references
    
    return result

def stream_message(message: str):
    """
    A simple generator that yields the given message.
    """
    yield message


def compress_text(text: str) -> str:
    """Compress and encode text using gzip and base64."""
    if not text:
        return ""
    compressed = gzip.compress(text.encode("utf-8"))
    return base64.b64encode(compressed).decode("utf-8")


def decompress_text(compressed_text: str) -> str:
    """Decode and decompress base64-encoded gzip text."""
    if not compressed_text:
        return ""
    compressed_bytes = base64.b64decode(compressed_text.encode("utf-8"))
    return gzip.decompress(compressed_bytes).decode("utf-8")
