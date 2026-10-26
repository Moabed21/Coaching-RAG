# Responsible for setting up the client, sending the messages/prompt to the 
# deployment model, and returning the completion output.

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Local Ollama 7B configuration (defaults to local Ollama qwen2.5:7b)

# endpoint = os.getenv("OLLAMA_BASE_URL")
# deployment_name = os.getenv("OLLAMA_MODEL")
# api_key = os.getenv("OLLAMA_API_KEY")

# Azure configurations (Tested and works properly)
endpoint = os.getenv("ENDPOINT")
deployment_name = os.getenv("MODEL_NAME")
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

def call_llm(messages: list) -> str:
    try:
        completion = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            temperature=0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[LLM Warning] Local Ollama call failed ({e}). Returning fallback.")
        return "Service temporarily unavailable. Please try again later."


def few_shot_caller(question : list[dict]) -> dict:
    # this function takes user question , makes calles to llm that generates examples to simplify the classification operation

    system_prompt = """You are a question classifier for an HR learning system.
    Classify the employee question into exactly one category:
    - "coaching" → course recommendations, training advice, skill development, or what courses to spend budget on
    - "policy"   → questions about policy rules, approval requirements, learning hours targets, or carrying over budget
    - "general"  → degree programmes (MBA/Masters), degree sponsorship, travel/hotel, or questions not covered in the documents
    Reply with ONLY the single word: coaching OR policy OR general"""

    full_message = [{"role":"system", "content" : system_prompt }] + question
    return call_llm (full_message).strip().lower()