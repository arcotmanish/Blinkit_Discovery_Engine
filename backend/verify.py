import asyncio
from collections import Counter
from db.client import supabase

run_id = 'a2a4743e-44be-4415-b1c5-de1737ac8a4d'

print('--- Phase 4 ---')
reviews = supabase.table('raw_reviews').select('status').eq('run_id', run_id).execute().data
status_counts = Counter(r['status'] for r in reviews)
print(f'Total reviews: {len(reviews)}')
print(f'Status distribution: {dict(status_counts)}')

print('\n--- Phase 5 ---')
chunks = supabase.table('review_chunks').select('*').eq('run_id', run_id).execute().data
print(f'Total chunks: {len(chunks)}')
annotations = supabase.table('chunk_annotations').select('*, review_chunks(chunk_text, review_id, raw_reviews(raw_text))').eq('run_id', run_id).execute().data
print(f'Total annotations: {len(annotations)}')
failed = [a for a in annotations if a.get('annotation_failed')]
print(f'Failed annotations: {len(failed)}')

evidence_types = Counter(a.get('decision_evidence_type') for a in annotations)
drivers = Counter(a.get('decision_driver') for a in annotations)
print(f'Evidence Types: {dict(evidence_types)}')
print(f'Drivers: {dict(drivers)}')

print('\nSample 5 Annotations:')
for i, a in enumerate(annotations[:5]):
    text = a.get('review_chunks', {}).get('chunk_text', '') if a.get('review_chunks') else 'N/A'
    print(f'\nSample {i+1}:')
    print(f'Chunk Text: {text.encode("ascii", "ignore").decode()}')
    evidence = str(a.get("evidence_quote"))
    print(f'Evidence Quote: {evidence.encode("ascii", "ignore").decode()}')
    print(f'Type: {a.get("decision_evidence_type")} | Driver: {a.get("decision_driver")}')

print('\n--- Phase 6a ---')
insights = supabase.table('synthesized_insights').select('*').eq('run_id', run_id).execute().data
print(f'Total synthesized insights: {len(insights)}')
for i in insights:
    print(f"- {i.get('title')} ({i.get('cluster_key')}) - Count: {i.get('evidence_count')}")

print('\n--- Phase 6b ---')
opps = supabase.table('opportunities').select('*').eq('run_id', run_id).execute().data
print(f'Total opportunities: {len(opps)}')
for o in opps:
    print(f"- {o.get('title')} | COM-B: {o.get('com_b_lever')}")
