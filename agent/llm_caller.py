# Responsible for setting up the client, sending the messages/prompt to the 
# deployment model, and returning the completion output.

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Local Ollama 7B configuration (defaults to local Ollama qwen2.5:7b)
base_url = os.getenv("OLLAMA_BASE_URL") 
deployment_name = os.getenv("OLLAMA_MODEL") 
api_key = os.getenv("OLLAMA_API_KEY") 

client = OpenAI(
    base_url=base_url,
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


