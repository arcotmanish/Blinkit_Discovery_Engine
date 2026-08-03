import asyncio
from db.client import supabase

run_id = 'a2a4743e-44be-4415-b1c5-de1737ac8a4d'

print('--- 10 RANDOM NONE ANNOTATIONS ---')
none_anns = supabase.table('chunk_annotations').select('*, review_chunks(chunk_text)').eq('run_id', run_id).eq('decision_evidence_type', 'none').limit(10).execute().data
for i, a in enumerate(none_anns):
    text = a.get('review_chunks', {}).get('chunk_text', '')
    if text:
        text = text.encode('ascii', 'ignore').decode()
    print(f'\n[None {i+1}]')
    print(f'Text: {text}')
    print(f'Observation: {a.get("customer_decision_observation")}')

print('\n--- AIRTEL SIM THEME EVIDENCE ---')
airtel = supabase.table('synthesized_insights').select('*').eq('run_id', run_id).ilike('title', '%Airtel%').execute().data
if airtel:
    print(airtel[0])
    chunk_ids = airtel[0].get('evidence_chunk_ids', [])
    for cid in chunk_ids:
        c = supabase.table('review_chunks').select('chunk_text').eq('id', cid).execute().data
        if c:
            text = c[0].get('chunk_text', '')
            if text:
                text = text.encode('ascii', 'ignore').decode()
            print(f'- Chunk Text: {text}')
else:
    print('No Airtel theme found.')
