"""
Gemini LLM wrapper — uses the current `google-genai` SDK.

Handles:
- JSON parse failure → retry once with stricter instructions
- API timeout → retry with exponential backoff
- Rate limit (429) → wait 60 seconds and retry
"""

import asyncio
import json
import re
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini 2.0 Flash as specified in the architecture doc
MODEL_NAME = "gemini-2.0-flash"

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _extract_json(text: str):
    """
    Extract JSON from model response text.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


async def call_llm_async(prompt: str, retry_count: int = 0) -> dict | list:
    """
    Async wrapper for Gemini API call with retry logic.
    """
    client = _get_client()

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            )
        )
        text = response.text
        return _extract_json(text)

    except json.JSONDecodeError:
        if retry_count < 1:
            strict_prompt = (
                prompt
                + "\n\nCRITICAL: Your previous response was not valid JSON. "
                "Return ONLY a raw JSON array. No markdown, no explanation, no code fences."
            )
            await asyncio.sleep(2)
            return await call_llm_async(strict_prompt, retry_count=retry_count + 1)
        raise

    except Exception as e:
        err_str = str(e)

        # Rate limit: wait 60 seconds
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            print(f"    [LLM] Rate limit hit. Waiting 60 seconds...")
            await asyncio.sleep(60)
            if retry_count < 2:
                return await call_llm_async(prompt, retry_count=retry_count + 1)
            raise

        # Timeout: exponential backoff
        if "timeout" in err_str.lower() or "deadline" in err_str.lower():
            wait = 5 * (2 ** retry_count)
            print(f"    [LLM] Timeout. Retrying in {wait}s...")
            await asyncio.sleep(wait)
            if retry_count < 2:
                return await call_llm_async(prompt, retry_count=retry_count + 1)
            raise

        raise
