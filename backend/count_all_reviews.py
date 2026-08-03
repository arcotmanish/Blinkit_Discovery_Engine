import sys
sys.path.insert(0, '.')
from db.client import supabase
from collections import Counter

with open("last_production_run.txt") as f:
    prod_run_id = f.read().strip()
print(f"Run: {prod_run_id}")

# Paginate through ALL rows to get the true count
all_rows = []
offset = 0
page_size = 1000
while True:
    res = supabase.table("raw_reviews")\
        .select("id,source,status,word_count")\
        .eq("run_id", prod_run_id)\
        .range(offset, offset + page_size - 1)\
        .execute()
    batch = res.data or []
    all_rows.extend(batch)
    print(f"  Fetched page at offset {offset}: {len(batch)} rows (cumulative: {len(all_rows)})")
    if len(batch) < page_size:
        break
    offset += page_size

print(f"\nActual total rows: {len(all_rows)}")

by_src = {}
for r in all_rows:
    src = r["source"]
    st = r["status"]
    by_src.setdefault(src, Counter())
    by_src[src][st] += 1

for src, cnt in by_src.items():
    total_src = sum(cnt.values())
    print(f"\n[{src}] total={total_src}")
    for status, n in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"  {status}: {n}")
