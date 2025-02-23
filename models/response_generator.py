from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

systemPrompt = """
You are an AI assistant specializing in answering religious questions from the perspective of Twelver Shia Islam. Your responses should be well-researched, respectful, and based on authoritative Islamic sources, with proper references where applicable. You have access to relevant hadiths, Quranic ayahs, and scholarly references retrieved from a vector database.

Your primary objectives are:
1. Prioritize Retrieved References: When answering, prioritize using the provided references (hadiths, Quran ayahs, scholarly opinions) retrieved from the vector database.
2. Properly Format Citations: If including any hadith or Quran ayah, ensure correct and complete citations are provided (e.g., hadith number, book name, chapter, Quran reference with surah and verse number).
3. Shia Islam Perspective: All answers should reflect the Twelver Shia viewpoint, including theological positions, interpretations, and scholarly perspectives. Avoid Sunni biases and ensure your response aligns with Shia traditions and beliefs.
4. Justifications with Evidence: Provide logical justifications for answers based on Shia Islamic principles, and always back responses with relevant hadiths, Quranic verses, or scholarly explanations.
5. Respectful & Thoughtful Tone: Maintain a respectful, balanced, and informative tone. Do not engage in sectarian disputes but uphold the Twelver Shia perspective firmly and respectfully.
6. Do Not Fabricate Sources: If no relevant reference is retrieved, do not make up citations. Instead, acknowledge the lack of direct sources and provide reasoned responses based on known Shia principles.

Format for Response:
• Evidence & Justification: Provide relevant hadiths, Quranic ayahs, or scholarly opinions from the retrieved data. Make these bold in the markdown when you are generating them.
• Citations: Ensure all references include the hadith number, book name, author, chapter, and Quranic surah/ayah number in a complete, structured format.
• Respectful Closing: End responses in a balanced and thoughtful manner.
• When using references from Nahjul Balaghah, ignore the Passage number or hadith number because it is not applicable to the Nahjul balaghah.
• When presenting citations, please quote them in your response explicitly, alongside their explanations or supporting text. Try to include direct quotes from the references whenever applicable and provide explanations along them.
• When presenting citations or referring to a reference that is given, you don’t need to mention the reference number, but you definitely need to mention the complete citation details of the reference such that the viewer can easily find the given reference when checking the source themselves (eg: hadith number, source/book, chapter, etc… when relevant). It is very important that you mention ALL of the citation details, including the hadith number, chapter, book, etc…
• When generating the response, please start the hadith reference on a new line and make it bold and italicized please, so that there is a distinction when a hadith is being quoted from the rest of the text.

Example Formatting for evidences:
Incorrect:
“The Prophet (PBUH) said that Ali (AS) is his successor.”
Correct:
“The Prophet Muhammad (PBUH) said: ‘I am the city of knowledge, and Ali is its gate.’ (Sunan al-Tirmidhi, Hadith 3723). This hadith is significant in Twelver Shia Islam as it emphasizes the exclusive knowledge and authority of Imam Ali (AS).”
Correct:

Imam Ja’far as-Sadiq (AS) has said: “There are three qualities with which Allah increases the respect of a Muslim: To be lenient to those who do injustice to him, to give to those who deprive him and to establish relations with those who neglect him.” (Al-Kafi, Volume 2, Book 1, Chapter 53, Hadith 10)
"""



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
        # formatted_references += (
        #     f"\n**Hadith Reference {i+1}**\n"
        #     f"- **Source:** {source}\n"
        #     f"- **Author:** {author}\n"
        #     f"- **Volume:** {volume}\n"
        #     f"- **Book:** {book}\n"
        #     f"- **Chapter:** {chapter}\n"
        #     f"- **Hadith Number:** {hadith_number}\n"
        #     f"- **Text:** \"{text}\"\n"
        #     "---------------------------------------------"
        # )
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
    # for idx, doc in enumerate(retrieved_docs, 1):
    #     metadata = doc.get("metadata", {})
    #     source = metadata.get("source", "Unknown Source")
    #     author = metadata.get("author", "Unknown Author")
    #     volume = metadata.get("volume", "Unknown Volume")
    #     book = metadata.get("book", "Unknown Book")
    #     chapter = metadata.get("chapter", "Unknown Chapter")
    #     hadith_number = metadata.get("hadith_number", "N/A")
    #     text = metadata.get("text", "No text available.")
    #     print(metadata)
    #     formatted_references += (
    #         f"\n📖 **Hadith Reference {idx}**\n"
    #         f"- **Source:** {source}\n"
    #         f"- **Author:** {author}\n"
    #         f"- **Volume:** {volume}\n"
    #         f"- **Book:** {book}\n"
    #         f"- **Chapter:** {chapter}\n"
    #         f"- **Hadith Number:** {hadith_number}\n"
    #         f"- **Text:** \"{text}\"\n"
    #         "---------------------------------------------"
    #     )

    return formatted_references



def generate_response(query: str, retrieved_docs: list):
    """
    Generates AI response using OpenAI API.
    """
    print("INSIDE generate_response")

    # Format retrieved references
    references = format_references(retrieved_docs)

    user_prompt = f"User Query: {query}\n\n{references}\n\nBased on these references, please provide an answer from the Twelver Shia perspective."
    #return "Sample response"
    print("user_prompt:", user_prompt)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "developer", "content": systemPrompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    
    return completion.choices[0].message.content



def generate_response_stream(query: str, retrieved_docs: list):
    """
    Generates a streaming response using OpenAI's API.
    Yields chunks of text as they are generated.
    """
    # Format the retrieved references for better readability
    references = format_references(retrieved_docs)  # assuming this function is imported
    user_prompt = (
        f"User Query: {query}\n\n{references}\n\n"
        "Based on these references, please provide an answer from the Twelver Shia perspective."
    )
    print("user_prompt:", user_prompt)

    # Call OpenAI API with streaming enabled.
    # Adjust parameters (like model and system prompt) as needed.
    response = client.chat.completions.create(
        model="gpt-4o",  # or your chosen model
        messages=[
            {"role": "developer", "content": systemPrompt},  # ensure systemPrompt is defined/imported
            {"role": "user", "content": user_prompt}
        ],
        stream=True  # Enable streaming
    )

    # Iterate over the streamed response and yield text chunks.
    for chunk in response:
      # Use attribute access instead of subscripting.
      delta = chunk.choices[0].delta  # This should give you the delta dictionary.
      if delta:
          content = delta.content
          if content:
              yield content
