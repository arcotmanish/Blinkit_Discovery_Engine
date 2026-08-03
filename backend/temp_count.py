import sys
from db.client import supabase

def main():
    res1 = supabase.table('chunk_annotations').select('chunk_id').execute()
    chunk_ids = [d['chunk_id'] for d in res1.data]
    
    all_chunks = []
    chunk_size = 500
    for i in range(0, len(chunk_ids), chunk_size):
        batch = chunk_ids[i:i+chunk_size]
        res2 = supabase.table('review_chunks').select('review_id').in_('id', batch).execute()
        all_chunks.extend(res2.data)
        
    unique_reviews = set([c.get('review_id') for c in all_chunks if c.get('review_id')])
    print(f'Count of unique reviews annotated: {len(unique_reviews)}')

if __name__ == '__main__':
    main()
