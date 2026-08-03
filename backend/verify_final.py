import asyncio
from db.client import supabase

run_id = 'a2a4743e-44be-4415-b1c5-de1737ac8a4d'

print('--- RESEARCH FIELDS VERIFICATION ---')
insights = supabase.table('synthesized_insights').select('*').eq('run_id', run_id).execute().data
if insights:
    sample = insights[0]
    print(f"corpus_percentage: {sample.get('corpus_percentage')}")
    print(f"is_strategic_theme: {sample.get('is_strategic_theme')}")
    print(f"suggested_interview_question: {sample.get('suggested_interview_question')}")
    print(f"suggested_survey_hypothesis: {sample.get('suggested_survey_hypothesis')}")
    print(f"source_distribution: {sample.get('source_distribution')}")

print('\n--- PAST EXPERIENCE THEME VERIFICATION (AIRTEL / DRIFT CHECK) ---')
# The cluster key was 'category_avoidance:past_experience'
drift_check = supabase.table('synthesized_insights').select('title, description').eq('run_id', run_id).eq('cluster_key', 'category_avoidance:past_experience').execute().data
if drift_check:
    print(f"Title: {drift_check[0].get('title')}")
    print(f"Description: {drift_check[0].get('description')}")
else:
    print("Theme not found.")

print('\n--- OPPORTUNITIES REGENERATION ---')
opps = supabase.table('opportunities').select('title, com_b_lever').eq('run_id', run_id).execute().data
print(f"Generated {len(opps)} opportunities.")
for o in opps:
    print(f"- {o.get('title')} ({o.get('com_b_lever')})")
