"""
Stage 3: Decision Evidence Extraction
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.client import supabase
from utils.llm import call_llm_async
from utils.text import chunk_review
from pipeline.prompts.extraction import build_extraction_prompt
import re

# PM Keyword Filter Words
CATEGORY_WORDS = ["grocery", "groceries", "snack", "snacks", "milk", "protein", "electronics",
                  "household", "bread", "oil", "eggs", "meat", "frozen", "dairy", "health",
                  "rice", "fruit", "vegetable", "shampoo", "stationery", "medicine", "baby",
                  "personal care", "pet", "beauty", "skincare", "detergent", "toothpaste", "nutrition"]
DISCOVERY_WORDS = ["first time", "for the first time", "tried", "discovered", "surprised",
                   "found out", "new product", "new category", "new item"]
REPETITION_WORDS = ["same product", "same items", "same thing", "always order", "regularly",
                    "routine", "repeat", "reorder", "habit", "weekly", "monthly"]
SWITCHING_WORDS = ["switched", "shifted", "changed", "moved to", "no longer",
                   "stopped ordering", "started buying", "started ordering",
                   "also ordered", "also tried"]
NUDGE_WORDS = ["recommend", "suggestion", "offer", "discount", "coupon", "deal", "notification", "browse", "wishlist"]

def build_pattern(words):
    escaped = [re.escape(w) for w in words]
    return re.compile(r'\b(?:' + '|'.join(escaped) + r')\b', re.IGNORECASE)

cat_pat = build_pattern(CATEGORY_WORDS)
disc_pat = build_pattern(DISCOVERY_WORDS)
rep_pat = build_pattern(REPETITION_WORDS)
sw_pat = build_pattern(SWITCHING_WORDS)
nudge_pat = build_pattern(NUDGE_WORDS)

BATCH_SIZE = 6
BATCH_DELAY_SECONDS = 2

async def extract_batch(batch: list) -> list:
    prompt = build_extraction_prompt([
        {
            'text': c['chunk_text'],
            'source': c.get('source', 'unknown'),
            'rating': c.get('rating', 'N/A'),
            'date': str(c.get('review_date', 'unknown')),
        }
        for c in batch
    ])
    
    try:
        result = await call_llm_async(prompt)
        if not isinstance(result, list):
            raise ValueError(f"Expected JSON array, got {type(result)}")
            
        for i, chunk in enumerate(batch):
            if i < len(result):
                chunk['annotation'] = result[i]
                chunk['annotation_failed'] = False
            else:
                chunk['annotation'] = None
                chunk['annotation_failed'] = True
    except Exception as e:
        err_str = str(e)
        print(f"    [Extract] Batch error: {err_str}")
        
        # FATAL ABORT: If this is a rate limit or quota exhaustion that bypassed the llm.py retries, 
        # it is likely a Daily Limit. We MUST halt the script to prevent marking all remaining chunks as failed.
        if "429" in err_str or "rate limit" in err_str.lower():
            print("    [FATAL] Quota Exhausted. Halting Stage 3 safely so it can be resumed later.")
            sys.exit(1)
            
        for chunk in batch:
            chunk['annotation'] = None
            chunk['annotation_failed'] = True
            
    return batch

async def run_stage_3(run_id: str):
    print(f"Starting Stage 3 (Extraction) for run: {run_id}")
    
    response = (
        supabase.table("raw_reviews")
        .select("id, cleaned_text, raw_text, source, rating, review_date")
        .eq("run_id", run_id)
        .in_("status", ["pending", "low_relevance", "relevant", "core_evidence"])
        .execute()
    )
    eligible = response.data or []
    print(f"  Found {len(eligible)} eligible reviews to chunk.")
    
    if not eligible:
        return
        
    review_meta = {r['id']: r for r in eligible}
    
    # 1. Fetch existing chunks for this run
    existing_chunks_resp = supabase.table("review_chunks").select("id, review_id, chunk_text").eq("run_id", run_id).limit(3000).execute()
    existing_chunks = existing_chunks_resp.data or []
    chunked_review_ids = set(c['review_id'] for c in existing_chunks)
    
    all_chunks = []
    
    # 2. Add existing chunks to our processing list
    for c in existing_chunks:
        r = review_meta.get(c['review_id'], {})
        all_chunks.append({
            "id": c['id'],
            "review_id": c['review_id'],
            "chunk_text": c['chunk_text'],
            "source": r.get('source'),
            "rating": r.get('rating'),
            "review_date": r.get('review_date')
        })
        
    # 3. Chunk and insert any new eligible reviews
    new_reviews = [r for r in eligible if r['id'] not in chunked_review_ids]
    if new_reviews:
        print(f"  Chunking {len(new_reviews)} new reviews...")
        for r in new_reviews:
            text = r.get('cleaned_text') or r.get('raw_text') or ''
            chunks = chunk_review(text)
            
            for i, c_text in enumerate(chunks):
                chunk_rec = {
                    "review_id": r['id'],
                    "run_id": run_id,
                    "chunk_index": i,
                    "chunk_text": c_text
                }
                try:
                    res = supabase.table("review_chunks").insert(chunk_rec).execute()
                    chunk_id = res.data[0]['id']
                    all_chunks.append({
                        "id": chunk_id,
                        "review_id": r['id'],
                        "chunk_text": c_text,
                        "source": r.get('source'),
                        "rating": r.get('rating'),
                        "review_date": r.get('review_date')
                    })
                except Exception as e:
                    print(f"Failed to insert chunk (index {i}) for review {r['id'][:8]}: {e}")
                    
    print(f"  Created/Loaded {len(all_chunks)} chunks for extraction.")
    
    # --- PM KEYWORD FILTER LOGIC ---
    print("\n  [PM Filter] Grouping chunks by review_id...")
    from collections import defaultdict
    review_to_chunks = defaultdict(list)
    for c in all_chunks:
        review_to_chunks[c['review_id']].append(c)
        
    filtered_chunks = []
    tier1_count = 0
    tier2_count = 0
    dropped_count = 0
    
    for rid, chunks in review_to_chunks.items():
        combined_text = " ".join([c['chunk_text'] for c in chunks])
        
        # Use finditer for category to count unique overlapping/multiple matches
        cat_matches = len(cat_pat.findall(combined_text))
        disc_match = bool(disc_pat.search(combined_text))
        rep_match = bool(rep_pat.search(combined_text))
        sw_match = bool(sw_pat.search(combined_text))
        nudge_match = bool(nudge_pat.search(combined_text))
        
        kept_tier = None
        
        # Tier 1
        if (disc_match or sw_match) and cat_matches >= 1:
            tier1_count += 1
            filtered_chunks.extend(chunks)
            kept_tier = "Tier 1"
        # Tier 2
        elif rep_match or cat_matches >= 2 or (nudge_match and cat_matches >= 1):
            tier2_count += 1
            filtered_chunks.extend(chunks)
            kept_tier = "Tier 2"
        else:
            dropped_count += 1
            
        if kept_tier:
            found_cats = set(m.group(0).lower() for m in cat_pat.finditer(combined_text))
            found_disc = set(m.group(0).lower() for m in disc_pat.finditer(combined_text))
            found_rep = set(m.group(0).lower() for m in rep_pat.finditer(combined_text))
            found_sw = set(m.group(0).lower() for m in sw_pat.finditer(combined_text))
            found_nudge = set(m.group(0).lower() for m in nudge_pat.finditer(combined_text))
            
            all_found = found_cats | found_disc | found_rep | found_sw | found_nudge
            print(f"[{kept_tier}] Review {rid[:8]} | Keywords: {', '.join(all_found)}")
            
    print(f"\n========================================")
    print(f" PM KEYWORD FILTER SUMMARY")
    print(f"========================================")
    print(f" Total Reviews Evaluated : {len(review_to_chunks)}")
    print(f" Tier 1 Kept             : {tier1_count}")
    print(f" Tier 2 Kept             : {tier2_count}")
    print(f" Total Reviews Kept      : {tier1_count + tier2_count}")
    print(f" Reviews Dropped         : {dropped_count}")
    print(f" Chunks Retained         : {len(filtered_chunks)} (out of {len(all_chunks)})")
    print(f"========================================\n")
    
    input("Press ENTER to confirm the filtered list and proceed to LLM Stage 3, or Ctrl+C to abort...")
    
    all_chunks = filtered_chunks
    # --- END PM FILTER ---
    
    # 4. Filter out chunks that have already been annotated
    annotated_resp = supabase.table("chunk_annotations").select("chunk_id").eq("run_id", run_id).limit(3000).execute()
    annotated_ids = set(a['chunk_id'] for a in (annotated_resp.data or []))
    
    pending_chunks = [c for c in all_chunks if c['id'] not in annotated_ids]
    print(f"  {len(pending_chunks)} chunks remaining to be annotated.")
    
    if not pending_chunks:
        print("  All chunks are already annotated.")
        return
    
    # Process batches
    total = len(pending_chunks)
    done = 0
    batches = [pending_chunks[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    
    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)}...", end=" ", flush=True)
        extracted = await extract_batch(batch)
        
        # Save annotations
        for chunk in extracted:
            if chunk.get('annotation_failed'):
                supabase.table("chunk_annotations").insert({
                    "chunk_id": chunk['id'],
                    "run_id": run_id,
                    "annotation_failed": True
                }).execute()
            else:
                ann = chunk['annotation']
                
                # Enforce Enums to prevent Postgres CHECK constraint violations
                valid_evidence_types = {"repeat_purchase", "category_avoidance", "category_exploration", "exploration_abandoned", "switching_behavior", "competitor_comparison", "impulse_consideration", "habitual_reorder", "none"}
                valid_drivers = {"trust", "quality_uncertainty", "habit", "convenience", "urgency", "availability", "price_sensitivity", "recommendation", "promotion", "navigation_difficulty", "past_experience", "none"}
                valid_contexts = {"weekly_routine", "emergency_need", "late_night", "family_household", "health_wellness", "festival_occasion", "gifting", "office_work", "routine_replenishment", "exploration_mindset", "none"}
                valid_segments = {"habitual_buyer", "reluctant_explorer", "trust_gated_shopper", "prompt_dependent_buyer", "dissatisfied_defector", "unclassified"}
                
                decision_evidence_type = ann.get('decision_evidence_type', 'none')
                if decision_evidence_type not in valid_evidence_types: decision_evidence_type = 'none'
                
                decision_driver = ann.get('decision_driver', 'none')
                if decision_driver not in valid_drivers: decision_driver = 'none'
                
                purchase_context = ann.get('purchase_context', 'none')
                if purchase_context not in valid_contexts: purchase_context = 'none'
                
                inferred_segment = ann.get('inferred_segment', 'unclassified')
                if inferred_segment not in valid_segments: inferred_segment = 'unclassified'
                
                try:
                    supabase.table("chunk_annotations").insert({
                        "chunk_id": chunk['id'],
                        "run_id": run_id,
                        "decision_evidence_type": decision_evidence_type,
                        "decision_driver": decision_driver,
                        "purchase_context": purchase_context,
                        "categories_mentioned": ann.get('categories_mentioned', []),
                        "evidence_quote": ann.get('evidence_quote'),
                        "other_signal": ann.get('other_signal'),
                        "inferred_segment": inferred_segment,
                        "confidence": ann.get('confidence', 'low'),
                        "annotation_failed": False
                    }).execute()
                except Exception as e:
                    print(f"    [Extract] Error inserting chunk {chunk['id']}: {e}")
                    # Insert it as failed so we don't infinitely retry it
                    supabase.table("chunk_annotations").insert({
                        "chunk_id": chunk['id'],
                        "run_id": run_id,
                        "annotation_failed": True
                    }).execute()
        
        done += len(batch)
        print(f"done. ({done}/{total} chunks annotated)")
        
        try:
            supabase.table("pipeline_runs").update({
                "stage_progress": {"extract": {"done": done, "total": total}}
            }).eq("id", run_id).execute()
        except:
            pass
            
        if batch_num < len(batches):
            await asyncio.sleep(BATCH_DELAY_SECONDS)

if __name__ == '__main__':
    try:
        with open("last_production_run.txt", "r") as f:
            run_id = f.read().strip()
        print(f"Using run: {run_id}")
        asyncio.run(run_stage_3(run_id))
    except Exception as e:
        print(f"Error: {e}")
