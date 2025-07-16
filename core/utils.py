from langchain_core.documents import Document
import traceback
import json

def format_references(retrieved_docs: list[Document]) -> str:
    """
    Formats retrieved hadiths and Quranic references for better readability.
    """
    print("INSIDE format_references")
    formatted_references = "\n\n**Retrieved References:**\n"

    try:
        if not retrieved_docs:
            return formatted_references + "\n(No relevant references were found in the database.)"

        for i in range(len(retrieved_docs)):
            source = retrieved_docs[i].metadata.get("source", "Unknown Source")
            author = retrieved_docs[i].metadata.get("author", "Unknown Author")
            volume = retrieved_docs[i].metadata.get("volume", "Unknown Volume")
            book = retrieved_docs[i].metadata.get("book", "Unknown Book")
            chapter = retrieved_docs[i].metadata.get("chapter", "Unknown Chapter")
            hadith_number = retrieved_docs[i].metadata.get("hadith_number", "N/A")
            if retrieved_docs[i].page_content is None or retrieved_docs[i].page_content.strip() == "":
                text = "No text available"
            else:
                text = retrieved_docs[i].page_content

            formatted_references += (
                f"\n--------------------------------------\n"
                f"- **Source:** {source}\n"
                f"- **Author:** {author}\n"
                f"- **Volume:** {volume}\n"
                f"- **Book:** {book}\n"
                f"- **Chapter:** {chapter}\n"
                f"- **Hadith Number:** {hadith_number}\n"
                f"- **Text:** \"{text}\"\n"
                "---------------------------------------------"
            )
            if i == 0:
                print(formatted_references)
    except Exception as e:
        print(f"Error formatting references: {e}")
        traceback.print_exc()
        formatted_references += "\n\n**Error formatting references. Please check the data structure.**"

    return formatted_references

def format_references_as_json(retrieved_docs: list[Document]):
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
                "source": doc.metadata.get("source", "Unknown Source"),
                "author": doc.metadata.get("author", "Unknown Author"),
                "volume": doc.metadata.get("volume", "Unknown Volume"),
                "book": doc.metadata.get("book", "Unknown Book"),
                "chapter": doc.metadata.get("chapter", "Unknown Chapter"),
                "hadith_number": doc.metadata.get("hadith_number", "N/A"),
                "text": doc.page_content.strip() if doc.page_content else "No text available"
            }
            formatted_references.append(reference)
    except Exception as e:
        print(f"Error formatting references: {e}")
        traceback.print_exc()
        return result
    
    result["references"] = formatted_references
    
    return '\n\n\n[REFERENCES]\n\n\n' + json.dumps(result)

def stream_message(message: str):
    """
    A simple generator that yields the given message.
    """
    yield message