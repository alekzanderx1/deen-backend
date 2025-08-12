from langchain_core.documents import Document
import traceback
import base64
import gzip

def format_references(retrieved_docs: list) -> str:
    """
    Formats retrieved hadiths and Quranic references for LLM-friendly Markdown output,
    aligned with the updated JSON structure used in `format_references_as_json`.
    """
    print("INSIDE format_references")
    header = "\n\n**Retrieved References:**\n"
    if not retrieved_docs:
        return header + "\n(No relevant references were found in the database.)"

    lines = [header]

    for idx, doc in enumerate(retrieved_docs, start=1):
        try:
            # Accept either plain dicts or LangChain Documents
            if isinstance(doc, dict):
                metadata = doc.get("metadata", {}) or {}
                page_content_en = doc.get("page_content_en", "") or ""
                page_content_ar = doc.get("page_content_ar", "") or ""
            else:
                # Fallback for LangChain Document objects
                metadata = getattr(doc, "metadata", {}) or {}
                # Your pipeline seems to store bilingual content separately; keep that behavior
                page_content_en = getattr(doc, "page_content_en", "") or getattr(doc, "page_content", "") or ""
                page_content_ar = getattr(doc, "page_content_ar", "") or ""

            author         = metadata.get("author", "N/A")
            volume         = metadata.get("volume", "N/A")
            book_number    = metadata.get("book_number", "N/A")
            book_title     = metadata.get("book_title", "N/A")
            chapter_number = metadata.get("chapter_number", "N/A")
            chapter_title  = metadata.get("chapter_title", "N/A")
            collection     = metadata.get("collection", "N/A")
            grade_ar       = metadata.get("grade_ar", "N/A")
            grade_en       = metadata.get("grade_en", "N/A")
            hadith_id      = metadata.get("hadith_id", "N/A")
            hadith_no      = metadata.get("hadith_no", "N/A")
            hadith_url     = metadata.get("hadith_url", "N/A")
            lang           = metadata.get("lang", "N/A")
            sect           = metadata.get("sect", "N/A")
            reference      = metadata.get("reference", "N/A")

            text_en = page_content_en.strip() if page_content_en else "No text available"
            text_ar = page_content_ar.strip() if page_content_ar else "No Arabic text available"

            block = [
                "--------------------------------------",
                f"**Reference {idx}:**",
                f"- **Book Title:** {book_title}",
                f"- **Author:** {author}",
                f"- **Volume:** {volume}",
                f"- **Book Number:** {book_number}",
                f"- **Chapter Number:** {chapter_number}",
                f"- **Chapter Title:** {chapter_title}",
                f"- **Collection:** {collection}",
                f"- **Hadith Number:** {hadith_no}",
                f"- **Hadith ID:** {hadith_id}",
                f"- **Reference:** {reference}",
                f"- **Grade (EN):** {grade_en}",
                f"- **Grade (AR):** {grade_ar}",
                f"- **Language:** {lang}",
                f"- **Sect:** {sect}",
                f"- **URL:** {hadith_url}" if hadith_url and hadith_url != "N/A" else None,
                f"- **Text (EN):** \"{text_en}\"",
                f"- **Text (AR):** \"{text_ar}\"",
                "---------------------------------------------",
            ]
            # Filter out Nones (e.g., URL line when missing)
            lines.append("\n".join([ln for ln in block if ln is not None]))

        except Exception as e:
            print(f"Error formatting a reference: {e}")
            traceback.print_exc()
            lines.append("**Error formatting a reference. Skipping this item.**")

    return "\n".join(lines)


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
    
    result = formatted_references
    
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
