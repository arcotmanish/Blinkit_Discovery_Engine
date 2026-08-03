"""
run_production_v2.py
--------------------
Smart production runner with corpus reuse.

Strategy:
  1. Detect an existing valid Google Play corpus in the last production run.
  2. If found and intact, copy those rows into the new run_id (bulk re-tag)
     instead of re-scraping Google Play.
  3. Collect only the missing sources: Reddit (fixed) + Apple App Store (graceful).
  4. Run the complete AI pipeline (Stage 2 → 6) on the new run_id.
  5. Write last_production_run.txt and generate the production report.

LLM calls begin at Stage 2 (Signal Scoring), AFTER all deterministic filtering is done.
No LLM is ever called before:
  - excluded_short filter (word_count < 10)
  - non_english filter (langdetect)
  - excluded_operational rule filter (Stage 2A, regex-based, before any LLM batch)
"""

import sys
import os
import uuid
import asyncio
import traceback
import time
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.client import supabase
from pipeline.stages.score import run_stage_2
from pipeline.stages.extract import run_stage_3
from pipeline.stages.synthesize import run_stage_5_synthesize
from pipeline.stages.opportunities import run_stage_6_opportunities
from pipeline.stages.vocab_qualify import run_stage_vocab_qualify
from scrapers import reddit, app_store
from utils.text import clean_text, count_words, hash_text, detect_language
from utils.llm import llm_stats


# ── Configuration ─────────────────────────────────────────────────────────────

SOURCE_LIMITS = {
    "play_store": 5000,   # Will be reused from existing run, not re-scraped
    "app_store":  500,    # RSS page 1 only → expect ~50 reviews
    "reddit":     1500,   # PullPush primary → Arctic Shift fallback (fixed)
}


# ── Corpus Reuse ───────────────────────────────────────────────────────────────

def find_reusable_gplay_corpus():
    """
    Look for an existing production run that has a substantial Google Play corpus
    with status=pending (i.e., never LLM-processed). Returns (run_id, count) or
    (None, 0) if no suitable corpus is found.
    """
    try:
        with open("last_production_run.txt") as f:
            prev_run_id = f.read().strip()
    except FileNotFoundError:
        print("  [Reuse] No last_production_run.txt found.")
        return None, 0

    # Paginate to get true count (Supabase caps at 1000 per request)
    all_rows = []
    offset = 0
    while True:
        res = supabase.table("raw_reviews") \
            .select("id,source,status,raw_text,cleaned_text,rating,review_date,source_url,content_hash,word_count,language") \
            .eq("run_id", prev_run_id) \
            .eq("source", "play_store") \
            .range(offset, offset + 999) \
            .execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    if not all_rows:
        print(f"  [Reuse] Previous run {prev_run_id[:8]}... has no Google Play data.")
        return None, 0

    # Check reusability: if any have been LLM-processed we still reuse them,
    # but Stage 2 will skip non-pending rows automatically.
    pending = [r for r in all_rows if r["status"] == "pending"]
    print(f"  [Reuse] Found {len(all_rows)} GP rows in {prev_run_id[:8]}... ({len(pending)} pending, {len(all_rows)-len(pending)} already processed)")
    return prev_run_id, all_rows


def copy_gplay_corpus_to_new_run(source_rows, new_run_id):
    """
    Bulk-copy Google Play rows from a previous run into new_run_id.
    Preserves all fields; resets status to 'pending' for rows that haven't
    been LLM-processed yet. Rows that were previously scored keep their status
    so Stage 2 will skip them correctly.
    """
    print(f"  Copying {len(source_rows)} Google Play rows → new run {new_run_id[:8]}...")
    inserted = 0
    skipped_dup = 0
    COPY_BATCH = 200

    for i in range(0, len(source_rows), COPY_BATCH):
        batch = source_rows[i:i + COPY_BATCH]
        rows_to_insert = []
        for r in batch:
            row = {
                "run_id": new_run_id,
                "source": "play_store",
                "raw_text": r["raw_text"],
                "cleaned_text": r["cleaned_text"],
                "rating": r["rating"],
                "review_date": r["review_date"],
                "source_url": r["source_url"],
                "content_hash": r["content_hash"],
                "word_count": r["word_count"],
                "language": r["language"],
                "status": r["status"],  # Preserve original status
            }
            rows_to_insert.append(row)

        for row in rows_to_insert:
            try:
                supabase.table("raw_reviews").insert(row).execute()
                inserted += 1
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "23505" in err or "conflict" in err:
                    skipped_dup += 1
                else:
                    print(f"    [Copy] Insert error: {e}")

        print(f"    Batch {i//COPY_BATCH + 1}: {inserted} inserted so far...")

    print(f"  [Reuse] Copy complete. {inserted} inserted, {skipped_dup} duplicates skipped.")
    return inserted


# ── Fresh Ingestion (Reddit + Apple) ─────────────────────────────────────────

def ingest_source(run_id, source_name, fetch_func, limit):
    """
    Ingest a single source: fetch -> clean -> filter -> deduplicate -> insert.
    Returns a full stats dict with keys:
      raw_fetched, inserted, excluded_short, non_english, duplicates, pending
    """
    print(f"\n  Fetching {source_name} (limit={limit})...")
    stats = {
        "raw_fetched": 0,
        "inserted": 0,
        "excluded_short": 0,
        "non_english": 0,
        "duplicates": 0,
        "pending": 0,
    }
    try:
        records = fetch_func(limit=limit)
    except Exception as e:
        print(f"  [Ingest] {source_name} fetch failed: {e}")
        return stats

    stats["raw_fetched"] = len(records)
    print(f"  Got {len(records)} raw records from {source_name}. Processing...")

    batch = []
    for r in records:
        raw_text = r.get("raw_text", "")
        cleaned = clean_text(raw_text)
        wc = count_words(cleaned)
        chash = hash_text(cleaned)

        if wc < 10:
            status = "excluded_short"
            stats["excluded_short"] += 1
            lang = "unknown"
        else:
            lang = detect_language(cleaned)
            if lang != "en":
                status = "non_english"
                stats["non_english"] += 1
            else:
                status = "pending"
                stats["pending"] += 1

        review_date = r.get("review_date")
        if review_date:
            review_date = str(review_date)

        row = {
            "run_id": run_id,
            "source": source_name,
            "raw_text": raw_text,
            "cleaned_text": cleaned,
            "rating": r.get("rating"),
            "review_date": review_date,
            "source_url": r.get("source_url"),
            "content_hash": chash,
            "word_count": wc,
            "language": lang,
            "status": status,
        }
        batch.append(row)

    for row in batch:
        try:
            supabase.table("raw_reviews").insert(row).execute()
            stats["inserted"] += 1
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "23505" in err or "conflict" in err:
                stats["duplicates"] += 1
                # Deduped rows are not pending — correct the pending count
                if row.get("status") == "pending":
                    stats["pending"] -= 1
            else:
                print(f"    [Ingest] Insert error: {e}")

    print(f"  [{source_name}] raw={stats['raw_fetched']} inserted={stats['inserted']} "
          f"excl_short={stats['excluded_short']} non_en={stats['non_english']} "
          f"dups={stats['duplicates']} pending={stats['pending']}")
    return stats


# ── Pre-run execution plan (estimates) ──────────────────────────────────────

def print_execution_plan(reuse_run_id, reuse_count, sources_to_collect):
    print()
    print("=" * 66)
    print("EXECUTION PLAN (estimates — actual numbers shown after ingestion)")
    print("=" * 66)
    if reuse_run_id and reuse_count > 0:
        print(f"REUSE:   Google Play corpus ({reuse_count} rows) from run {reuse_run_id[:8]}...")
        print(f"         -> Rows copied verbatim. Google Play scraper WILL NOT run.")
    else:
        print("COLLECT: Google Play (no reusable corpus found — will scrape fresh)")

    for src, limit in sources_to_collect:
        print(f"COLLECT: {src} (limit={limit})")

    print()
    print("LLM calls begin at Stage 2B, AFTER all deterministic filters:")
    print("  [Stage 1 det.]  excluded_short        word_count < 10")
    print("  [Stage 1 det.]  non_english           langdetect filter")
    print("  [Stage 1 det.]  content_hash          deduplication")
    print("  [Stage 2A det.] excluded_operational  regex rule filter (wc<15, patterns)")
    print("  [Stage 2B LLM]  <<< FIRST LLM CALL >>> signal scoring, batch=5")
    print("  [Stage 3  LLM]  chunk extraction + annotation, batch=2")
    print("  [Stage 4  LLM]  cluster merge decisions")
    print("  [Stage 5  LLM]  theme synthesis per cluster")
    print("  [Stage 6  LLM]  opportunity generation (1 call)")
    print("=" * 66)
    print()


# ── Pre-LLM ingestion summary (actual counts, pauses for confirmation) ──────

def print_pre_llm_summary_and_confirm(run_id, source_stats, auto_confirm=False):
    """
    Queries the DB for final per-source counts, renders a formatted table,
    and pauses for explicit operator confirmation before Stage 2B begins.
    Stage 2A (rule filter) runs INSIDE run_stage_2 before any LLM batch,
    so this summary shows the pre-2A state (i.e., 'pending' rows entering Stage 2).
    """
    from collections import Counter

    # Query actual DB state — paginate for large corpora
    all_rows = []
    offset = 0
    while True:
        res = supabase.table("raw_reviews") \
            .select("source,status,word_count") \
            .eq("run_id", run_id) \
            .range(offset, offset + 999) \
            .execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    by_src = {}
    for r in all_rows:
        src = r["source"]
        st = r["status"]
        by_src.setdefault(src, Counter())
        by_src[src][st] += 1

    total_pending = sum(
        cnt.get("pending", 0) for cnt in by_src.values()
    )
    total_rows = len(all_rows)

    print()
    print("=" * 66)
    print("PRE-LLM INGESTION SUMMARY (actual DB counts)")
    print("=" * 66)
    print(f"{'Source':<14} {'Collected':>10} {'Excl.Short':>11} {'Non-EN':>7} {'Dups':>6} {'Pending->LLM':>13}")
    print("-" * 66)

    src_order = ["play_store", "reddit", "app_store"]
    for src in src_order:
        if src not in by_src:
            continue
        cnt = by_src[src]
        total_src = sum(cnt.values())
        excl = cnt.get("excluded_short", 0)
        non_en = cnt.get("non_english", 0)
        # Duplicates not stored in DB (rejected at insert), use ingestion stats
        dups = source_stats.get(src, {}).get("duplicates", 0)
        pending = cnt.get("pending", 0)
        print(f"  {src:<12} {total_src:>10,} {excl:>11,} {non_en:>7,} {dups:>6,} {pending:>13,}")

    print("-" * 66)
    print(f"  {'TOTAL':<12} {total_rows:>10,} {'':>11} {'':>7} {'':>6} {total_pending:>13,}")
    print("=" * 66)
    print()

    # ── LLM Workload Estimates ──
    est_n2 = int(total_pending * 0.9)  # assume 10% filtered by Stage 2A (operational/short)
    est_score_calls = est_n2 // 5      # batch=5
    est_n3 = int(est_n2 * 0.20)        # assume 20% yield pass scoring to extraction
    est_extract_calls = est_n3 // 2    # batch=2
    est_other_calls = 50               # Aggregate (15-30), Synthesize (10-15), Opportunities (1)
    
    est_total_calls = est_score_calls + est_extract_calls + est_other_calls
    est_tokens = est_total_calls * 1800
    est_runtime_mins = max(1, est_total_calls // 22)  # ~22 calls/min based on past run
    
    print("==================================================================")
    print("ESTIMATED LLM WORKLOAD & COST (Groq / llama-3.3-70b-versatile)")
    print("==================================================================")
    print(f"  Stage 2B (Signal Scoring): ~{est_score_calls:>6,} API calls (batch=5)")
    print(f"  Stage 3 (Extraction):      ~{est_extract_calls:>6,} API calls (batch=2, est. 20% yield)")
    print(f"  Stages 4-6 (Agg/Synth):    ~{est_other_calls:>6,} API calls")
    print("-" * 66)
    print(f"  Total Groq Requests:       ~{est_total_calls:>6,} calls")
    print(f"  Estimated Tokens:          ~{est_tokens:>10,} tokens")
    print(f"  Estimated Runtime:         ~{est_runtime_mins:>6} minutes")
    print("==================================================================")
    print()

    print(f"  {total_pending:,} reviews will now enter Stage 2A (rule filter) then Stage 2B (LLM scoring).")
    print(f"  Stage 2A is deterministic — it filters further before any LLM call.")
    print()
    if auto_confirm:
        print("  [AUTO-CONFIRM] Proceeding to LLM scoring (--auto-confirm flag set).")
    else:
        answer = input("  CONFIRM: Type 'yes' to begin LLM scoring, or Ctrl+C to abort: ").strip().lower()
        if answer != "yes":
            print("  Aborted by operator. All ingested data is preserved in the DB.")
            raise SystemExit(0)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def run_all(auto_confirm=False):
    # Step 1: Find reusable GP corpus
    print("\n[Step 1] Checking for reusable Google Play corpus...")
    reuse_run_id, gplay_rows = find_reusable_gplay_corpus()

    is_reused_run = False
    if reuse_run_id and gplay_rows:
        new_run_id = reuse_run_id
        is_reused_run = True
        print("=" * 60)
        print(f"BLINKIT DISCOVERY ENGINE — PRODUCTION RUN v2")
        print(f"Resuming run ID: {new_run_id} (using existing corpus)")
    else:
        new_run_id = str(uuid.uuid4())
        print("=" * 60)
        print(f"BLINKIT DISCOVERY ENGINE — PRODUCTION RUN v2")
        print(f"New run ID: {new_run_id}")

    if auto_confirm:
        print("[MODE: --auto-confirm — all prompts will be bypassed]")
    print("=" * 60)

    # Decide what to collect fresh
    sources_to_collect = [
        ("reddit", SOURCE_LIMITS["reddit"]),
    ]
    # Apple is always attempted (graceful fail — only 50 reviews from page 1)
    sources_to_collect.append(("app_store", SOURCE_LIMITS["app_store"]))

    # Print execution plan
    print_execution_plan(reuse_run_id, len(gplay_rows) if gplay_rows else 0, sources_to_collect)

    if auto_confirm:
        print("[AUTO-CONFIRM] Proceeding with execution (--auto-confirm flag set).")
    else:
        input("Press ENTER to confirm and begin execution, or Ctrl+C to abort: ")

    # Step 2: Create pipeline_run record
    if not is_reused_run:
        try:
            supabase.table("pipeline_runs").insert({
                "id": new_run_id,
                "mode": "live",
                "status": "running"
            }).execute()
            print(f"[OK] Created pipeline_run {new_run_id}")
        except Exception as e:
            print(f"[ERROR] Failed to create pipeline_run: {e}")
            return
    else:
        # Update existing run to running status in case it was aborted
        supabase.table("pipeline_runs").update({"status": "running"}).eq("id", new_run_id).execute()

    # Track per-source ingestion stats for the pre-LLM summary
    all_source_stats = {}

    # Step 3: Corpus reuse — track GP rows
    if is_reused_run:
        print(f"\n[Step 3] Reusing {len(gplay_rows)} Google Play rows from run {new_run_id}...")
        # Build synthetic stats for the summary table
        from collections import Counter
        gp_status_counts = Counter(r["status"] for r in gplay_rows)
        all_source_stats["play_store"] = {
            "raw_fetched": len(gplay_rows),
            "inserted": len(gplay_rows),
            "excluded_short": gp_status_counts.get("excluded_short", 0),
            "non_english": gp_status_counts.get("non_english", 0),
            "duplicates": 0,
            "pending": gp_status_counts.get("pending", 0),
        }
    else:
        print("\n[Step 3] No reusable corpus found. Running Google Play scraper...")
        from scrapers import play_store as ps_mod
        all_source_stats["play_store"] = ingest_source(
            new_run_id, "play_store", ps_mod.fetch, SOURCE_LIMITS["play_store"]
        )

    # Step 4: Collect fresh sources
    print("\n[Step 4] Collecting fresh sources...")

    # Reddit (with Arctic Shift fix)
    time.sleep(1)
    all_source_stats["reddit"] = ingest_source(
        new_run_id, "reddit", reddit.fetch, SOURCE_LIMITS["reddit"]
    )

    # Apple App Store (graceful — page 1 only, expect ~50 reviews)
    time.sleep(1)
    print("\n  [Apple App Store] Attempting collection (page 1 only, graceful fail)...")
    apple_stats = ingest_source(
        new_run_id, "app_store", app_store.fetch, SOURCE_LIMITS["app_store"]
    )
    all_source_stats["app_store"] = apple_stats
    if apple_stats["inserted"] == 0:
        print("  [Apple] 0 reviews inserted. Continuing (expected if endpoint returns empty).")

    # Save the run ID only after ingestion completes successfully
    with open("last_production_run.txt", "w") as f:
        f.write(new_run_id)

    # Step 5: Pre-LLM ingestion summary + confirmation gate
    print("\n[Step 5] All ingestion complete. Preparing pre-LLM summary...")
    print_pre_llm_summary_and_confirm(new_run_id, all_source_stats, auto_confirm=auto_confirm)

    # Step 6: AI Pipeline
    ai_stages = [
        ("Vocab Qualify",           lambda: asyncio.run(run_stage_vocab_qualify(new_run_id))),
        ("Score (Stage 2)",         lambda: asyncio.run(run_stage_2(new_run_id))),
        ("Extract (Stage 3)",       lambda: asyncio.run(run_stage_3(new_run_id))),
        ("Synthesize (Stage 5+4)",  lambda: asyncio.run(run_stage_5_synthesize(new_run_id))),
        ("Opportunities (Stage 6)", lambda: asyncio.run(run_stage_6_opportunities(new_run_id))),
    ]

    print("\n[Step 6] Running AI pipeline...")
    for name, func in ai_stages:
        print(f"\n--- {name} ---")
        try:
            func()
            print(f"[OK] {name} complete.")
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            traceback.print_exc()
            supabase.table("pipeline_runs").update({
                "status": f"failed_at_{name.lower().replace(' ', '_')}"
            }).eq("id", new_run_id).execute()
            print("Preserving all completed work. Pipeline stopped.")
            llm_stats.print_summary()
            return

    # Step 7: Mark run complete
    try:
        supabase.table("pipeline_runs").update({"status": "completed"}).eq("id", new_run_id).execute()
        print(f"\n[OK] Production pipeline {new_run_id} completed successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to update final status: {e}")

    llm_stats.print_summary()

    # Step 8: Generate report
    print("\n[Step 8] Generating production report...")
    try:
        import subprocess
        subprocess.run(
            ["venv\\Scripts\\python", "generate_production_report.py"],
            check=True
        )
    except Exception as e:
        print(f"[WARN] Report generation failed: {e} — run generate_production_report.py manually.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blinkit Discovery Engine — Production Run v2")
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Bypass all interactive input() prompts (for headless / CI execution)"
    )
    args = parser.parse_args()
    run_all(auto_confirm=args.auto_confirm)
