import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.llm import call_llm_async

async def test():
    prompt = """Return ONLY valid JSON. No explanation. No markdown:
[{"signal_score": 0.75, "rationale": "API connectivity test."}]"""
    result = await call_llm_async(prompt)
    print("Gemini API test:", result)

asyncio.run(test())
