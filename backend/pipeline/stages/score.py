"""
Stage 2: Signal Scoring Pipeline

Hybrid approach:
  Sub-stage A — Rule-based exclusion (fast, no LLM cost)
  Sub-stage B — LLM batch scoring via Gemini 2.0 Flash (5 reviews per call)

Rate limiting: asyncio.sleep(4) between batches → max ~15 RPM on free tier.
"""

import asyncio
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.client import supabase
from utils.llm import call_llm_async
from pipeline.prompts.signal_scoring import build_scoring_prompt

# ── Constants ──────────────────────────────────────────────────────────────────

BATCH_SIZE = 5
BATCH_DELAY_SECONDS = 4  # Keeps us safely under 15 RPM on free tier

# Operational-only patterns (rule-based exclusion)
OPERATIONAL_PATTERNS = [
    r'\botp\b',
    r'\bone.time.pass',
    r'app.crash',
    r'app.not.work',
    r'app.is.not.open',
    r'customer.support',
    r'customer.care',
    r'delivery.partner',
    r'delivery.boy',
    r'delivery.agent',
    r'delivery.person',
    r'payment.fail',
    r'payment.not.work',
    r'refund.not.receiv',
    r'can.?t.log',
    r'login.issue',
    r'account.block',
]

# If these keywords appear, the review may still have behavioral signal
BEHAVIORAL_KEYWORDS = [
    r'\brepeat\b', r'\bregular\b', r'\balways\b', r'\busually\b',
    r'\bswitch\b', r'\bcompare\b', r'\bprefer\b', r'\bchoose\b',
    r'\bavoid\b', r'\btrust\b', r'\bbrand\b', r'\bcategory\b',
    r'\bselection\b', r'\bvariety\b', r'\boption\b', r'\balternative\b',
    r'\bbetter than\b', r'\bworse than\b', r'\binstead\b',
    r'\bzepto\b', r'\binstamart\b', r'\bamazon\b', r'\bswiggy\b',
    r'\bblinkit\b', r'\bgrofers\b',
]

# ── Status mapping ─────────────────────────────────────────────────────────────

def score_to_status(score: float) -> str:
    if score < 0.20:
        return 'excluded_operational'
    elif score < 0.40:
        return 'archived'
    elif score < 0.60:
        return 'low_relevance'
    elif score < 0.80:
        return 'relevant'
    else:
        return 'core_evidence'

# ── Sub-stage A: Rule-based pre-filter ────────────────────────────────────────

def _is_operational_only(text: str) -> bool:
    """
    Returns True if the text matches operational patterns AND has no behavioral keywords.
    """
    text_lower = text.lower()
    has_operational = any(re.search(p, text_lower) for p in OPERATIONAL_PATTERNS)
    if not has_operational:
        return False
    has_behavioral = any(re.search(k, text_lower) for k in BEHAVIORAL_KEYWORDS)
    return not has_behavioral


def apply_rule_filter(reviews: list) -> tuple[list, list]:
    """
    Separates reviews into (to_score, excluded).
    Mutates excluded with status='excluded_operational'.
    """
    to_score = []
    excluded = []

    for r in reviews:
        text = r.get('cleaned_text') or r.get('raw_text') or ''
        word_count = r.get('word_count', len(text.split()))

        if word_count < 15:
            r['_new_status'] = 'excluded_operational'
            r['_reason'] = 'word_count < 15'
            excluded.append(r)
        elif _is_operational_only(text):
            r['_new_status'] = 'excluded_operational'
            r['_reason'] = 'operational_only_pattern'
            excluded.append(r)
        else:
            to_score.append(r)

    return to_score, excluded


# ── Sub-stage B: LLM batch scoring ────────────────────────────────────────────

async def score_batch(batch: list) -> list:
    """
    Score a batch of up to BATCH_SIZE reviews using Gemini.
    Returns the batch with _signal_score and _signal_rationale set.
    """
    prompt = build_scoring_prompt([
        {
            'text': (r.get('cleaned_text') or r.get('raw_text') or '')[:800],
            'source': r.get('source', 'unknown'),
            'rating': r.get('rating', 'N/A'),
            'date': str(r.get('review_date', 'unknown')),
        }
        for r in batch
    ])

    try:
        result = await call_llm_async(prompt)

        # result should be a list of {signal_score, rationale}
        if not isinstance(result, list):
            raise ValueError(f"Expected list, got {type(result)}")

        for i, r in enumerate(batch):
            if i < len(result):
                item = result[i]
                r['_signal_score'] = float(item.get('signal_score', 0.5))
                r['_signal_rationale'] = str(item.get('rationale', ''))
                r['_new_status'] = score_to_status(r['_signal_score'])
            else:
                # Partial response fallback
                r['_signal_score'] = 0.5
                r['_signal_rationale'] = 'Partial LLM response — default score assigned'
                r['_new_status'] = 'low_relevance'

    except Exception as e:
        print(f"    [Score] Batch error: {e}. Assigning default scores.")
        for r in batch:
            r['_signal_score'] = 0.5
            r['_signal_rationale'] = f'LLM error: {str(e)[:100]}'
            r['_new_status'] = 'low_relevance'

    return batch


# ── Database helpers ───────────────────────────────────────────────────────────

def _update_review(review_id: str, updates: dict):
    supabase.table("raw_reviews").update(updates).eq("id", review_id).execute()


def _flush_excluded(excluded: list):
    """Write rule-excluded rows to DB immediately — no LLM cost."""
    for r in excluded:
        _update_review(r['id'], {
            'status': 'excluded_operational',
            'signal_score': 0.0,
            'signal_rationale': r.get('_reason', 'rule-based exclusion'),
        })


def _flush_scored(scored: list):
    """Write LLM-scored rows to DB."""
    for r in scored:
        _update_review(r['id'], {
            'status': r['_new_status'],
            'signal_score': r['_signal_score'],
            'signal_rationale': r['_signal_rationale'],
        })


def _update_run_progress(run_id: str, done: int, total: int):
    try:
        supabase.table("pipeline_runs").update({
            "stage_progress": {"score": {"done": done, "total": total}}
        }).eq("id", run_id).execute()
    except Exception:
        pass  # Non-critical


# ── Main entry point ───────────────────────────────────────────────────────────

async def run_stage_2(run_id: str):
    """
    Run Stage 2 Signal Scoring on all pending reviews for the given run_id.
    """
    print(f"Starting Stage 2 (Signal Scoring) for run: {run_id}")

    # Fetch all pending reviews for this run
    response = (
        supabase.table("raw_reviews")
        .select("id, raw_text, cleaned_text, word_count, rating, review_date, source, status")
        .eq("run_id", run_id)
        .eq("status", "pending")
        .execute()
    )
    pending = response.data or []
    print(f"  Found {len(pending)} pending reviews.")

    if not pending:
        print("  Nothing to score. Stage 2 complete.")
        return

    # Sub-stage A: Rule-based filter
    to_score, excluded = apply_rule_filter(pending)
    print(f"  Rule filter: {len(excluded)} excluded, {len(to_score)} sent to LLM.")

    _flush_excluded(excluded)

    # Sub-stage B: LLM batch scoring
    total = len(to_score)
    done = 0
    batches = [to_score[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    print(f"  Scoring {total} reviews in {len(batches)} batches of {BATCH_SIZE}...")

    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)}...", end=" ", flush=True)
        scored_batch = await score_batch(batch)
        _flush_scored(scored_batch)
        done += len(scored_batch)
        print(f"done. ({done}/{total} scored)")
        _update_run_progress(run_id, done, total)

        if batch_num < len(batches):
            await asyncio.sleep(BATCH_DELAY_SECONDS)

    print(f"Stage 2 complete. {len(excluded)} rule-excluded, {done} LLM-scored.")


if __name__ == '__main__':
    import uuid

    # Find the most recent pipeline_run or create a test one
    try:
        runs = supabase.table("pipeline_runs").select("id").order("created_at", desc=True).limit(1).execute()
        if runs.data:
            run_id = runs.data[0]['id']
            print(f"Using existing run: {run_id}")
        else:
            run_id = str(uuid.uuid4())
            supabase.table("pipeline_runs").insert({"id": run_id, "mode": "live", "status": "running"}).execute()
            print(f"Created new run: {run_id}")
    except Exception as e:
        run_id = str(uuid.uuid4())
        print(f"Could not query runs ({e}), using new run_id: {run_id}")

    asyncio.run(run_stage_2(run_id))
