from dotenv import load_dotenv
load_dotenv()
from db.client import supabase
from collections import Counter, defaultdict

run_id = 'a2a4743e-44be-4415-b1c5-de1737ac8a4d'

rows = supabase.table('raw_reviews').select('source, status, word_count, language, cleaned_text').eq('run_id', run_id).execute().data

by_source_status = defaultdict(Counter)
for r in rows:
    by_source_status[r['source']][r['status']] += 1

print('=== STATUS BREAKDOWN BY SOURCE ===')
for src, ctr in by_source_status.items():
    print(src + ': ' + str(dict(ctr)))

print('\n=== SAMPLE NON-ENGLISH (possible misclassification check) ===')
non_eng = [r for r in rows if r['status'] == 'non_english']
print(f'Total non_english: {len(non_eng)}')
for r in non_eng[:15]:
    text = (r.get('cleaned_text') or '')[:120].encode('ascii', 'ignore').decode()
    wc = r.get('word_count')
    lang = r.get('language')
    print('  lang=' + str(lang) + ' | wc=' + str(wc) + ' | text: ' + text)

print('\n=== EXCLUDED_SHORT reviews sample ===')
short_revs = [r for r in rows if r['status'] == 'excluded_short']
print(f'Total excluded_short: {len(short_revs)}')
for r in short_revs[:10]:
    text = (r.get('cleaned_text') or '')[:120].encode('ascii', 'ignore').decode()
    wc = r.get('word_count')
    lang = r.get('language')
    print('  lang=' + str(lang) + ' | wc=' + str(wc) + ' | text: ' + text)
