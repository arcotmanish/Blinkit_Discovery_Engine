import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
run_id = os.environ.get("DEMO_RUN_ID", "4a58551b-b5fd-469e-803f-b8871cab3a42")

def fetch_all(table, columns, eq_col, eq_val):
    all_data = []
    page = 0
    size = 1000
    while True:
        start = page * size
        end = start + size - 1
        resp = supabase.table(table).select(columns).eq(eq_col, eq_val).range(start, end).execute()
        data = resp.data or []
        all_data.extend(data)
        if len(data) < size:
            break
        page += 1
    return all_data

print("Fetching all original chunks using pagination...")
all_chunks = fetch_all("review_chunks", "id, review_id, chunk_text", "run_id", run_id)
print(f"Total chunks in DB: {len(all_chunks)}")

print("Fetching all annotations using pagination...")
all_annotations = fetch_all("chunk_annotations", "chunk_id", "run_id", run_id)
annotated_ids = set(a['chunk_id'] for a in all_annotations)
print(f"Total unique annotated chunks in DB: {len(annotated_ids)}")

# Let's count how many chunks are actually missing annotations!
missing = [c for c in all_chunks if c['id'] not in annotated_ids]
print(f"Total exact chunks missing annotations (including duplicates and noise): {len(missing)}")

# To be exact, let's run the PM filter on all_chunks to get the 445 high-value chunks.
from pipeline.stages.extract import check_tier1, check_tier2

tier1_reviews = []
tier2_reviews = []

chunks_by_review = {}
for c in all_chunks:
    chunks_by_review.setdefault(c['review_id'], []).append(c)

for rid, chunks in chunks_by_review.items():
    full_text = " ".join([c['chunk_text'] for c in chunks])
    t1 = check_tier1(full_text)
    t2 = check_tier2(full_text)
    if t1:
        tier1_reviews.append(rid)
    elif t2:
        tier2_reviews.append(rid)

pm_kept_rids = set(tier1_reviews + tier2_reviews)
pm_kept_chunks = [c for c in all_chunks if c['review_id'] in pm_kept_rids]

print(f"Total high-value chunks after PM filter: {len(pm_kept_chunks)}")

missing_high_value = [c for c in pm_kept_chunks if c['id'] not in annotated_ids]
print(f"==================================================")
print(f"EXACT NUMBER OF HIGH-VALUE CHUNKS MISSING: {len(missing_high_value)}")
print(f"==================================================")
