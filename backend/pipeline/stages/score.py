"""
Stage 4: Signal Scoring
=======================
Pure aggregation — NO LLM calls. Reads chunk_annotations, computes
frequency/percentage scores per signal dimension, then writes to
the signal_scores table in Supabase.

Run standalone:  python pipeline/stages/score.py
"""

import os
import sys
import json
from collections import Counter
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def fetch_all(table: str, columns: str = "*") -> list:
    all_data, page, size = [], 0, 1000
    while True:
        start = page * size
        resp = supabase.table(table).select(columns).range(start, start + size - 1).execute()
        data = resp.data or []
        all_data.extend(data)
        if len(data) < size:
            break
        page += 1
    return all_data


def pct(count: int, total: int) -> float:
    return round((count / total) * 100, 1) if total else 0.0


# ─────────────────────────────────────────────
# Compute scores (pure Python, zero LLM calls)
# ─────────────────────────────────────────────

def compute_scores(annotations: list) -> dict:
    # Skip annotation failures
    valid = [a for a in annotations if not a.get("annotation_failed")]
    total = len(valid)

    driver_counts   = Counter(a["decision_driver"]          for a in valid if a.get("decision_driver"))
    context_counts  = Counter(a["purchase_context"]         for a in valid if a.get("purchase_context"))
    evidence_counts = Counter(a["decision_evidence_type"]   for a in valid if a.get("decision_evidence_type"))
    segment_counts  = Counter(a["inferred_segment"]         for a in valid if a.get("inferred_segment"))
    conf_counts     = Counter(a["confidence"]               for a in valid if a.get("confidence"))

    # Categories mentioned is a list field — flatten all lists
    all_cats = []
    for a in valid:
        cats = a.get("categories_mentioned") or []
        all_cats.extend(cats)
    category_counts = Counter(all_cats)

    # Cross-pattern: decision_driver × purchase_context
    cross: Counter = Counter()
    for a in valid:
        d = a.get("decision_driver") or "none"
        c = a.get("purchase_context") or "none"
        cross[(d, c)] += 1

    top_cross = [
        {"driver": k[0], "context": k[1], "count": v, "pct": pct(v, total)}
        for k, v in cross.most_common(10)
    ]

    def to_list(counter, limit=None):
        items = counter.most_common(limit)
        return [{"key": k, "count": v, "pct": pct(v, total)} for k, v in items]

    return {
        "total_annotations":      total,
        "decision_driver":        to_list(driver_counts),
        "purchase_context":       to_list(context_counts),
        "decision_evidence_type": to_list(evidence_counts),
        "inferred_segment":       to_list(segment_counts),
        "confidence":             to_list(conf_counts),
        "categories_mentioned":   to_list(category_counts, 15),
        "cross_patterns":         top_cross,
    }


# ─────────────────────────────────────────────
# Pretty-print preview
# ─────────────────────────────────────────────

def print_preview(scores: dict):
    total = scores["total_annotations"]
    sep   = "─" * 56

    print()
    print("=" * 62)
    print("  STAGE 4 — SIGNAL SCORING PREVIEW")
    print("=" * 62)
    print(f"  Total valid annotations : {total}")
    print()

    sections = [
        ("TOP DECISION DRIVERS",        scores["decision_driver"][:8]),
        ("TOP PURCHASE CONTEXTS",       scores["purchase_context"]),
        ("DECISION EVIDENCE TYPES",     scores["decision_evidence_type"]),
        ("INFERRED USER SEGMENTS",      scores["inferred_segment"]),
        ("CATEGORIES MENTIONED",        scores["categories_mentioned"][:10]),
        ("CONFIDENCE DISTRIBUTION",     scores["confidence"]),
    ]

    for title, rows in sections:
        print(f"  {title}")
        print(f"  {sep}")
        for i, row in enumerate(rows, 1):
            bar = "█" * max(1, int(row["pct"] / 2))
            print(f"  {i:>2}. {row['key']:<35} {row['count']:>4}  ({row['pct']:>5.1f}%)  {bar}")
        print()

    print("  TOP CROSS-PATTERNS  (Decision Driver × Purchase Context)")
    print(f"  {sep}")
    for i, cp in enumerate(scores["cross_patterns"], 1):
        print(f"  {i:>2}. {cp['driver']:<30} × {cp['context']:<25} {cp['count']:>4}")
    print()


# ─────────────────────────────────────────────
# Save to Supabase signal_scores table
# ─────────────────────────────────────────────

def save_scores(scores: dict, run_id: str):
    rows = []

    for dim in ["decision_driver", "purchase_context",
                "decision_evidence_type", "inferred_segment",
                "confidence", "categories_mentioned"]:
        for entry in scores[dim]:
            rows.append({
                "run_id":      run_id,
                "signal_type": dim,
                "signal_key":  entry["key"],
                "signal_key2": None,
                "count":       entry["count"],
                "percentage":  entry["pct"],
            })

    for cp in scores["cross_patterns"]:
        rows.append({
            "run_id":      run_id,
            "signal_type": "cross_pattern",
            "signal_key":  cp["driver"],
            "signal_key2": cp["context"],
            "count":       cp["count"],
            "percentage":  cp["pct"],
        })

    # Insert in chunks of 100
    for i in range(0, len(rows), 100):
        supabase.table("signal_scores").insert(rows[i: i + 100]).execute()

    print(f"  Saved {len(rows)} signal score rows to Supabase.")


# ─────────────────────────────────────────────
# Main (interactive gate)
# ─────────────────────────────────────────────

def main():
    print("\nFetching annotations from database...")
    annotations = fetch_all("chunk_annotations")
    print(f"  Loaded {len(annotations)} annotation rows.")

    scores = compute_scores(annotations)

    # Determine the dominant run_id
    run_ids = Counter(a.get("run_id") for a in annotations if a.get("run_id"))
    run_id  = run_ids.most_common(1)[0][0] if run_ids else "unknown"

    print_preview(scores)

    print("=" * 62)
    answer = input("  Press ENTER to save scores to DB, or type 'n' to abort: ").strip().lower()
    if answer == "n":
        print("  Aborted. Nothing saved.")
        sys.exit(0)

    save_scores(scores, run_id)
    print("  Stage 4 complete. You can now run Stage 5 (synthesize.py).")
    print("=" * 62)


if __name__ == "__main__":
    main()
