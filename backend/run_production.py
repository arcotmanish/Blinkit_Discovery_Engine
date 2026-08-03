import sys
import os
import uuid
import asyncio
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.client import supabase
from pipeline.stages.ingest import run_stage_1
from pipeline.stages.score import run_stage_2
from pipeline.stages.extract import run_stage_3
from pipeline.stages.synthesize import run_stage_5_synthesize
from pipeline.stages.opportunities import run_stage_6_opportunities

def run_all():
    prod_run_id = str(uuid.uuid4())
    print(f"==================================================")
    print(f"STARTING PRODUCTION DISCOVERY RUN: {prod_run_id}")
    print(f"==================================================")

    try:
        # DB schema expects 'live' or 'demo'. We'll insert 'live' but pass 'production' to stages.
        supabase.table("pipeline_runs").insert({"id": prod_run_id, "mode": "live", "status": "running"}).execute()
        print(f"[OK] Created pipeline_run {prod_run_id}")
    except Exception as e:
        print(f"[ERROR] Failed to create pipeline_run: {e}")
        return

    # Write the run ID to file so reporting script can find it
    with open("last_production_run.txt", "w") as f:
        f.write(prod_run_id)

    stages = [
        ("Ingest", lambda: run_stage_1(prod_run_id, mode='production')),
        ("Score", lambda: asyncio.run(run_stage_2(prod_run_id))),
        ("Extract", lambda: asyncio.run(run_stage_3(prod_run_id))),
        ("Synthesize", lambda: asyncio.run(run_stage_5_synthesize(prod_run_id))),
        ("Opportunities", lambda: asyncio.run(run_stage_6_opportunities(prod_run_id))),
    ]

    for name, func in stages:
        print(f"\n--- Starting {name} ---")
        try:
            func()
            print(f"[OK] {name} completed.")
        except Exception as e:
            print(f"[ERROR] {name} failed: {e}")
            traceback.print_exc()
            print("Preserving completed work. Stopping pipeline.")
            supabase.table("pipeline_runs").update({"status": f"failed_at_{name.lower()}"}).eq("id", prod_run_id).execute()
            return
            
    try:
        supabase.table("pipeline_runs").update({"status": "completed"}).eq("id", prod_run_id).execute()
        print(f"\n[OK] Production pipeline {prod_run_id} completed successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to update final status: {e}")

if __name__ == "__main__":
    run_all()
