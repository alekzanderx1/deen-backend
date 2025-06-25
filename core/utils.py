def format_references(retrieved_docs: list) -> str:
    """
    Formats retrieved hadiths and Quranic references for better readability.
    """
    print("INSIDE format_references")
    formatted_references = "\n\n**Retrieved References:**\n"

    if not retrieved_docs:
        return formatted_references + "\n(No relevant references were found in the database.)"
    # print(retrieved_docs)
    for i in range(len(retrieved_docs)):
        source = retrieved_docs[i].get("source", "Unknown Source")
        author = retrieved_docs[i].get("author", "Unknown Author")
        volume = retrieved_docs[i].get("volume", "Unknown Volume")
        book = retrieved_docs[i].get("book", "Unknown Book")
        chapter = retrieved_docs[i].get("chapter", "Unknown Chapter")
        hadith_number = retrieved_docs[i].get("hadith_number", "N/A")
        text = retrieved_docs[i].get("text", "No text available.")

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

    return formatted_references

def stream_message(message: str):
    """
    A simple generator that yields the given message.
    """
    yield message