# import torch
# from transformers import AutoModelForCausalLM, AutoTokenizer


# # Load Qwen Model for Classification
# MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
# device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
# model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to(device)

from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


systemPromptForFiqh = """
Task:
Your task is to classify the following user query as fiqh-related (Islamic jurisprudence) or not.

Instructions:
• Respond with only one word: “true” if the query is related to fiqh, and “false” if it is not.
• Do not provide any explanations, additional text, or commentary—only respond with “true” or “false”.
• A query is considered fiqh-related if it pertains to Islamic legal rulings on acts of worship, transactions, family law, halal/haram issues, penalties, contracts, purification, prayer, fasting, zakat, marriage, inheritance, and similar jurisprudential matters.
• A query is non-fiqh-related if it pertains to history, theology, philosophy, spirituality, tafsir (Quranic exegesis), hadith interpretation, ethics, politics, science, general knowledge, or other non-legal Islamic topics.

Examples for classification:

Fiqh-Related Queries (Respond with “true”)
1. Is it permissible to fast while traveling? → true
2. What are the conditions for performing ghusl? → true
3. Can I combine my Dhuhr and Asr prayers while traveling? → true
4. Is interest (riba) haram in Islam? → true
5. What nullifies wudu? → true
6. Is seafood halal according to Twelver Shia jurisprudence? → true
7. What are the requirements for a valid Islamic marriage contract? → true
8. Can I give zakat to my poor brother? → true
9. What should I do if I forget a raka’ah in prayer? → true
10. How is inheritance divided in Islamic law? → true

Non-Fiqh Queries (Respond with “false”)
1. What is the meaning of Surah Al-Ikhlas? → false
2. Why do Shia Muslims commemorate Ashura? → false
3. What did Imam Ali (AS) say about justice? → false
4. Who was the first Imam in Shia Islam? → false
5. What are the main beliefs of Twelver Shia Islam? → false
6. What is the historical significance of Karbala? → false
7. Who compiled Nahj al-Balagha? → false
8. What does the Quran say about patience? → false
9. What was the relationship between Imam Jafar al-Sadiq (AS) and Abu Hanifa? → false
10. What is the meaning of Tawheed? → false
"""

systemPromptForNonIslamicFilter = """
Your task is to determine whether the given user query is irrelevant or inappropriate for an Islamic educational chatbot focused on Twelver Shia Islam.
• If the query is irrelevant (e.g., unrelated to Islam, asking about random topics, celebrities, general trivia, math problems, politics, technology, science, or anything outside Islamic studies), respond with “true”.
• If the query is appropriate (i.e., related to Islam, Quran, Hadith, Islamic history, Shia beliefs, jurisprudence, spirituality, theology, ethics, philosophy, or Islamic scholars), respond with “false”.
• Only respond with “true” or “false”. Do not provide any explanation or additional text.

Irrelevant/Inappropriate Queries (Respond with “true”)
1. Who is Mark Zuckerberg? → true
2. Why is the Earth flat? → true
3. Who is Donald Trump? → true
4. What is the product of 2 and 5? → true
5. How do I invest in cryptocurrency? → true

Relevant Queries (Respond with “false”)
1. What is the meaning of Surah Al-Ikhlas? → false
2. Why do Shia Muslims commemorate Ashura? → false
3. What did Imam Ali (AS) say about justice? → false
4. Who was the first Imam in Shia Islam? → false
5. What are the main beliefs of Twelver Shia Islam? → false

"""


def classify_fiqh_query(query: str) -> bool:
    """
    Uses Qwen to determine if a query is fiqh-related or not.
    Returns True if fiqh-related, False otherwise.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": systemPromptForFiqh},
            {"role": "user", "content": query}
        ]
    )

    response = completion.choices[0].message.content

    return "true" in response.lower()



def classify_non_islamic_query(query: str) -> bool:
    """
    Uses 4o mini to classify whether the user query is relevant to shia islam or not
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": systemPromptForNonIslamicFilter},
            {"role": "user", "content": query}
        ]
    )

    response = completion.choices[0].message.content

    return "true" in response.lower()

