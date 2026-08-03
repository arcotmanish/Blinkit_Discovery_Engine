import sys
sys.path.insert(0, '.')
from db.client import supabase
from collections import Counter

# 1. All pipeline runs
print("=== Pipeline Runs (most recent 10) ===")
runs = supabase.table("pipeline_runs").select("id,mode,status,started_at,completed_at").order("started_at", desc=True).limit(10).execute()
for r in runs.data:
    started = (r.get("started_at") or "?")[:19]
    print(f"  {r['id']} | {r['mode']} | {r['status']} | {started}")

print()

# 2. Get the last production run ID
with open("last_production_run.txt") as f:
    prod_run_id = f.read().strip()
print(f"Last production run: {prod_run_id}")
print()

# 3. Raw reviews breakdown per source + status for that run
print("=== Raw Reviews in Production Run ===")
res = supabase.table("raw_reviews").select("id,source,status,word_count").eq("run_id", prod_run_id).execute()
rows = res.data
print(f"Total rows in run: {len(rows)}")

by_src = {}
for r in rows:
    src = r["source"]
    st = r["status"]
    by_src.setdefault(src, Counter())
    by_src[src][st] += 1

for src, cnt in by_src.items():
    total_src = sum(cnt.values())
    print(f"  [{src}] total={total_src}")
    for status, n in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"    {status}: {n}")

print()

# 4. Check how many English-pending reviews exist (these are what Stage 2 would process)
pending_en = [r for r in rows if r["status"] == "pending"]
print(f"English pending (would go to LLM scoring): {len(pending_en)}")

print()

# 5. Check downstream stages
print("=== Downstream Stage Data for This Run ===")

def safe_count(result):
    if hasattr(result, "count") and result.count is not None:
        return result.count
    return len(result.data)

r_chunks = supabase.table("review_chunks").select("id", count="exact").eq("run_id", prod_run_id).execute()
r_annots = supabase.table("chunk_annotations").select("id", count="exact").eq("run_id", prod_run_id).execute()
r_insights = supabase.table("synthesized_insights").select("id", count="exact").eq("run_id", prod_run_id).execute()
r_opps = supabase.table("opportunities").select("id", count="exact").eq("run_id", prod_run_id).execute()

print(f"  review_chunks:         {safe_count(r_chunks)}")
print(f"  chunk_annotations:     {safe_count(r_annots)}")
print(f"  synthesized_insights:  {safe_count(r_insights)}")
print(f"  opportunities:         {safe_count(r_opps)}")

print()
print("=== Reusability Assessment ===")
gp_rows = [r for r in rows if r["source"] == "play_store"]
gp_pending = [r for r in gp_rows if r["status"] == "pending"]
gp_other = [r for r in gp_rows if r["status"] not in ("pending", "excluded_short", "non_english")]
print(f"  Google Play total:     {len(gp_rows)}")
print(f"  GP pending (usable):   {len(gp_pending)}")
print(f"  GP already processed:  {len(gp_other)}")
print(f"  GP excluded/short:     {len([r for r in gp_rows if r['status'] in ('excluded_short','non_english')])}")
