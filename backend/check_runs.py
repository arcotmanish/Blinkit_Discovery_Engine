from db.client import supabase
all_data = []
page = 0
size = 1000
while True:
    res = supabase.table('raw_reviews').select('run_id').range(page*size, (page+1)*size-1).execute().data
    if not res:
        break
    all_data.extend(res)
    page += 1
from collections import Counter
print(Counter(r['run_id'] for r in all_data))
