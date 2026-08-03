import os
import asyncio
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

from utils.llm import call_llm_async

async def main():
    print("Testing new Groq API Key...")
    print(f"Key loaded: {os.getenv('GROQ_API_KEY')[:8]}...")
    
    prompt = "Please respond with a simple JSON object like this: {\"status\": \"success\"}. Do not output any markdown."
    
    try:
        result = await call_llm_async(prompt)
        print("Success! LLM responded with:")
        print(result)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
