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

systemPrompt = """
You are an AI assistant for a Twelver Shia Islam application, enhancing user queries to improve their clarity and context while keeping them within the original intent. Your task is to refine the given user question so that it remains faithful to its original meaning but adds slight elaboration or necessary context to make it clearer for retrieval in a knowledge database.

Enhance the following user query while ensuring that:
It retains the same intent and meaning.
It includes relevant clarifications or disambiguations if the query is vague.
It improves completeness by making implicit details more explicit.
It remains concise and does not add unnecessary complexity.

Example Enhancements:

Example 1:

User Query: “Who was the first Imam?”
Enhanced Query: “Who was the first Imam in Twelver Shia Islam, and what was his significance?”

Example 2:

User Query: “Why do Shias commemorate Ashura?”
Enhanced Query: “What is the significance of Ashura in Shia Islam, and why do Shia Muslims commemorate this event?”

Example 3:

User Query: “What is Taqiyya?”
Enhanced Query: “What does the concept of Taqiyya mean in Shia Islam, and in what circumstances is it applied?”
"""

def enhance_query(query: str) -> str:
    """
    Enhances user query by adding more context to improve retrieval.
    """
    print("INSIDE enhance_query")
    # messages = [
    #     {"role": "system", "content": systemPrompt},
    #     {"role": "user", "content": query}
    # ]

    # text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # model_inputs = tokenizer([text], return_tensors="pt").to(device)

    # generated_ids = model.generate(**model_inputs, max_new_tokens=50)

    # generated_ids = [
    #   output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    # ]

    # enhanced_query = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # print("Generated enhanced query:", enhanced_query)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": systemPrompt},
            {"role": "user", "content": query}
        ]
    )

    enhanced_query = completion.choices[0].message.content

    print("Generated enhanced query:", enhanced_query)

    return enhanced_query.strip()