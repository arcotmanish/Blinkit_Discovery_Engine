import sys
import os
from typing import Dict, Any, List

# Setup path for standalone execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.client import supabase
from scrapers import play_store, app_store, reddit
from utils.text import clean_text, count_words, hash_text, detect_language

def run_stage_1(run_id: str, mode: str = 'live', allowed_sources: List[str] = None):
    """
    Run Stage 1 Ingestion: Scrape, Clean, Hash, Detect Lang, Insert.
    Mode 'production' fetches thousands, 'demo' 700, 'live' 50.
    """
    print(f"Starting Stage 1 (Ingest) - mode: {mode}")
    
    if mode == 'production':
        source_limits = {'play_store': 5000, 'app_store': 500, 'reddit': 1500}
    elif mode == 'demo':
        source_limits = {'play_store': 700, 'app_store': 700, 'reddit': 700}
    else:
        source_limits = {'play_store': 50, 'app_store': 50, 'reddit': 50}
    
    all_sources = {
        'play_store': play_store.fetch,
        'app_store': app_store.fetch,
        'reddit': reddit.fetch
    }
    
    if not allowed_sources:
        allowed_sources = list(all_sources.keys())
        
    sources = [(k, v) for k, v in all_sources.items() if k in allowed_sources]
    
    stats = {'play_store': 0, 'app_store': 0, 'reddit': 0, 'duplicates_skipped': 0, 'non_english': 0, 'excluded_short': 0}
    
    for source_name, fetch_func in sources:
        limit = source_limits.get(source_name, 100)
        print(f"Fetching from {source_name} with limit {limit}...")
        try:
            records = fetch_func(limit=limit)
        except Exception as e:
            print(f"Failed to fetch {source_name}: {e}")
            continue
            
        print(f"Got {len(records)} raw records from {source_name}. Processing...")
        
        batch = []
        for r in records:
            raw_text = r.get('raw_text', '')
            cleaned = clean_text(raw_text)
            wc = count_words(cleaned)
            
            chash = hash_text(cleaned)
            
            status = 'pending'
            if wc < 10:
                # Too short to contain meaningful behavioral signal.
                # The signal scoring stage also has a < 15 word rule, but filtering
                # here saves API quota by never sending these to scoring at all.
                # Threshold is 10 (not 15) to be conservative — see Architecture P6.
                status = 'excluded_short'
                stats['excluded_short'] += 1
                lang = 'unknown'
            else:
                lang = detect_language(cleaned)
                if lang != 'en':
                    status = 'non_english'
                    stats['non_english'] += 1
            review_date = r.get('review_date')
            if review_date:
                review_date = str(review_date)
                
            row = {
                "run_id": run_id,
                "source": source_name,
                "raw_text": raw_text,
                "cleaned_text": cleaned,
                "rating": r.get('rating'),
                "review_date": review_date,
                "source_url": r.get('source_url'),
                "content_hash": chash,
                "word_count": wc,
                "language": lang,
                "status": status
            }
            batch.append(row)
            
        if batch:
            print(f"Inserting {len(batch)} records into DB for {source_name}...")
            inserted = 0
            for item in batch:
                try:
                    supabase.table("raw_reviews").insert(item).execute()
                    inserted += 1
                    stats[source_name] += 1
                except Exception as e:
                    err_str = str(e).lower()
                    if 'duplicate key value' in err_str or '23505' in err_str or 'conflict' in err_str:
                        stats['duplicates_skipped'] += 1
                    else:
                        print(f"Error inserting: {e}")
                        
            print(f"Inserted {inserted} new records from {source_name}.")
            
    print(f"Stage 1 Complete. Stats: {stats}")
    return stats

if __name__ == '__main__':
    import uuid
    test_run_id = str(uuid.uuid4())
    print(f"Creating dummy pipeline_run: {test_run_id}")
    try:
        supabase.table("pipeline_runs").insert({"id": test_run_id, "mode": "live", "status": "running"}).execute()
        run_stage_1(test_run_id, mode='live')
    except Exception as e:
        print(f"Error: {e}")
