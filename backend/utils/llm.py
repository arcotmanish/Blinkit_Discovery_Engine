"""
Groq LLM wrapper — uses the `groq` SDK.

Handles:
- JSON parse failure → retry once with stricter instructions
- API timeout → retry with exponential backoff
- Rate limit (429) → wait 60 seconds and retry; on repeated 429s, raises
  so the caller can abort without writing dummy data.

Observability:
- A module-level RunStats instance (llm_stats) accumulates token usage,
  retry counts, and failure counts across the entire pipeline run.
- Call llm_stats.print_summary() at the end of a run for a full report.
"""

import asyncio
import json
import re
import os
from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq model
MODEL_NAME = "llama-3.3-70b-versatile"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=GROQ_API_KEY)
    return _client


# ── Runtime statistics ─────────────────────────────────────────────────────────

class RunStats:
    """
    Lightweight in-memory accumulator for Groq API call statistics.

    One module-level instance (llm_stats) is shared across all pipeline
    stages for the duration of a single script run. It resets automatically
    when the process restarts.

    Counters:
        successful_calls  — API calls that returned a parseable JSON response.
        retried_calls     — Additional API calls made due to JSON or transient errors.
        failed_calls      — Calls that exhausted all retries and raised.
        quota_failures    — 429 / TPD quota exhaustion errors encountered.
        json_failures     — JSONDecodeError events that triggered a retry.
        prompt_tokens     — Cumulative prompt tokens from successful responses.
        completion_tokens — Cumulative completion tokens from successful responses.
    """

    __slots__ = (
        "successful_calls",
        "retried_calls",
        "failed_calls",
        "quota_failures",
        "json_failures",
        "prompt_tokens",
        "completion_tokens",
    )

    def __init__(self):
        self.successful_calls = 0
        self.retried_calls = 0
        self.failed_calls = 0
        self.quota_failures = 0
        self.json_failures = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def avg_tokens_per_success(self) -> float:
        if self.successful_calls == 0:
            return 0.0
        return self.total_tokens / self.successful_calls

    def print_summary(self):
        total = self.successful_calls + self.failed_calls
        print("\n" + "=" * 62)
        print("GROQ API — RUN STATISTICS")
        print("=" * 62)
        print(f"  Model                        : {MODEL_NAME}")
        print(f"  Successful API calls         : {self.successful_calls:>10,}")
        print(f"  Retried calls (transient err): {self.retried_calls:>10,}")
        print(f"  Failed calls (gave up)       : {self.failed_calls:>10,}")
        print(f"  Quota / 429 failures         : {self.quota_failures:>10,}")
        print(f"  JSON parse failures (retried): {self.json_failures:>10,}")
        print("-" * 62)
        print(f"  Prompt tokens                : {self.prompt_tokens:>10,}")
        print(f"  Completion tokens            : {self.completion_tokens:>10,}")
        print(f"  Total tokens                 : {self.total_tokens:>10,}")
        if self.successful_calls:
            print(f"  Avg tokens / successful call : {self.avg_tokens_per_success:>10,.1f}")
        print("=" * 62)


# Module-level singleton — imported by run_production_v2.py for the final summary.
llm_stats = RunStats()


# ── JSON extraction ────────────────────────────────────────────────────────────

def _extract_json(text: str):
    """
    Extract JSON from model response text.
    Handles cases where the model wraps JSON in markdown code blocks.
    """
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)


# ── Main call wrapper ──────────────────────────────────────────────────────────

async def call_llm_async(prompt: str, retry_count: int = 0) -> dict | list:
    """
    Async wrapper for Groq API call with retry logic and statistics tracking.

    Stats are recorded as follows:
    - successful_calls / token counts: only on a clean API + JSON success.
    - retried_calls:   incremented every time we recurse (any retry reason).
    - json_failures:   incremented when JSONDecodeError triggers a retry.
    - quota_failures:  incremented on every 429 encounter.
    - failed_calls:    incremented when we exhaust retries and re-raise.
    """
    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        # Capture token usage before parsing — parsing may still raise.
        usage = response.usage
        text = response.choices[0].message.content
        parsed = _extract_json(text)

        # Only record success + tokens once we know the JSON is valid.
        llm_stats.successful_calls += 1
        if usage:
            llm_stats.prompt_tokens += usage.prompt_tokens or 0
            llm_stats.completion_tokens += usage.completion_tokens or 0

        return parsed

    except json.JSONDecodeError:
        llm_stats.json_failures += 1
        if retry_count < 1:
            llm_stats.retried_calls += 1
            strict_prompt = (
                prompt
                + "\n\nCRITICAL: Your previous response was not valid JSON. "
                "Return ONLY a raw JSON array. No markdown, no explanation, no code fences."
            )
            await asyncio.sleep(2)
            return await call_llm_async(strict_prompt, retry_count=retry_count + 1)
        llm_stats.failed_calls += 1
        raise

    except Exception as e:
        err_str = str(e)

        # Rate limit / quota exhaustion — record and retry up to limit.
        if "429" in err_str or "rate limit" in err_str.lower():
            llm_stats.quota_failures += 1
            print(f"    [LLM] Rate limit hit. Waiting 60 seconds...")
            await asyncio.sleep(60)
            if retry_count < 2:
                llm_stats.retried_calls += 1
                return await call_llm_async(prompt, retry_count=retry_count + 1)
            llm_stats.failed_calls += 1
            raise

        # Timeout / service unavailable — exponential backoff.
        if "timeout" in err_str.lower() or "deadline" in err_str.lower() or "503" in err_str:
            wait = 5 * (2 ** retry_count)
            print(f"    [LLM] Timeout/Unavailable. Retrying in {wait}s...")
            await asyncio.sleep(wait)
            if retry_count < 2:
                llm_stats.retried_calls += 1
                return await call_llm_async(prompt, retry_count=retry_count + 1)
            llm_stats.failed_calls += 1
            raise

        llm_stats.failed_calls += 1
        raise
