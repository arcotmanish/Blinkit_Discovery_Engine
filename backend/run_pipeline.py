import sys
import os
import argparse
import asyncio
from typing import List

# Setup path for standalone execution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.stages.ingest import run_stage_1
from pipeline.stages.vocab_qualify import run_stage_vocab_qualify
from pipeline.stages.extract import run_stage_3
from pipeline.stages.score import fetch_all, compute_scores, save_scores

async def run_pipeline(run_id: str, sources: List[str]):
    print("=" * 60)
    print(f"🚀 STARTING PIPELINE LAUNCHER")
    print(f"Run ID: {run_id}")
    print(f"Sources: {', '.join(sources)}")
    print("=" * 60)
    
    # Register Run in Database
    from db.client import supabase
    try:
        supabase.table("pipeline_runs").insert({"id": run_id, "status": "running", "mode": "live"}).execute()
    except Exception as e:
        print(f"[WARNING] Could not register pipeline run (might already exist): {e}")

    # 1. Scraping (Stage 1)
    print("\n[STAGE 1] Ingestion & Scraping")
    run_stage_1(run_id=run_id, mode='live', allowed_sources=sources)
    
    # 2. Vocabulary Filter (Stage 2)
    print("\n[STAGE 2] Behaviour Vocabulary Filter")
    await run_stage_vocab_qualify(run_id=run_id)
    
    # 3. LLM Extraction (Stage 3)
    print("\n[STAGE 3] LLM Chunk Extraction")
    await run_stage_3(run_id=run_id)
    
    # 4. Scoring (Stage 4)
    print("\n[STAGE 4] Signal Scoring")
    # Fetch ONLY annotations for this run_id
    from db.client import supabase
    res = supabase.table("chunk_annotations").select("*").eq("run_id", run_id).execute()
    annotations = res.data or []
    
    if not annotations:
        print("  No annotations found for this run. Skipping scoring.")
    else:
        print(f"  Computing scores for {len(annotations)} annotations...")
        scores = compute_scores(annotations)
        save_scores(scores, run_id)
        
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Automated Pipeline Orchestrator")
    parser.add_argument("--run-id", type=str, required=True, help="Unique UUID for this execution")
    parser.add_argument("--sources", type=str, required=True, help="Comma separated list of sources (e.g., app_store,play_store)")
    
    args = parser.parse_args()
    sources_list = [s.strip() for s in args.sources.split(",")]
    
    asyncio.run(run_pipeline(args.run_id, sources_list))

if __name__ == "__main__":
    main()
