import sys
sys.path.insert(0, '.')
from db.client import supabase
from collections import Counter

REAL_CORPUS_RUN = '4a58551b-b5fd-469e-803f-b8871cab3a42'

# Valid statuses seem to be: running, completed, failed_* — try 'failed'
# For runs with data we'll just leave them as-is (they're harmless old runs)

runs = supabase.table('pipeline_runs').select('id,status,mode').neq('id', REAL_CORPUS_RUN).execute()
print('Remaining pipeline runs:')
for r in runs.data:
    rid = r['id']
    chk = supabase.table('raw_reviews').select('id', count='exact').eq('run_id', rid).execute()
    cnt = chk.count if chk.count is not None else len(chk.data)
    print(f'  {rid}  status={r["status"]}  raw_reviews={cnt}')
    if cnt == 0:
        supabase.table('pipeline_runs').delete().eq('id', rid).execute()
        print('    -> DELETED')
    else:
        print('    -> leaving as-is (has data, won\'t interfere)')

# Restore last_production_run.txt
with open('last_production_run.txt', 'w') as f:
    f.write(REAL_CORPUS_RUN)
print()
print(f'last_production_run.txt = {REAL_CORPUS_RUN}')

# Verify GP corpus
all_rows = []
offset = 0
while True:
    res = supabase.table('raw_reviews') \
        .select('id,status') \
        .eq('run_id', REAL_CORPUS_RUN) \
        .eq('source', 'play_store') \
        .range(offset, offset + 999) \
        .execute()
    batch = res.data or []
    all_rows.extend(batch)
    if len(batch) < 1000:
        break
    offset += 1000

status_counts = Counter(r['status'] for r in all_rows)
print(f'GP corpus: {len(all_rows)} rows => {dict(status_counts)}')
print('READY.')
