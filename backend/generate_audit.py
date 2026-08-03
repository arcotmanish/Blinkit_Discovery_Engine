import os
import sys
from db.client import supabase

run_id = 'a2a4743e-44be-4415-b1c5-de1737ac8a4d'

def generate_audit():
    # 1. Fetch all raw reviews for the run
    reviews_res = supabase.table('raw_reviews').select('id, source, raw_text, status').eq('run_id', run_id).execute().data
    
    # 2. Fetch all insights to map chunk_id -> theme title
    insights = supabase.table('synthesized_insights').select('title, evidence_chunk_ids').eq('run_id', run_id).execute().data
    chunk_to_theme = {}
    for ins in insights:
        for cid in ins.get('evidence_chunk_ids', []):
            chunk_to_theme[cid] = ins.get('title')
            
    # Group reviews by source
    by_source = {}
    for r in reviews_res:
        src = r.get('source')
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(r)
        
    md_content = ["# Dataset Audit: Current Run\n", f"**Run ID:** `{run_id}`\n\n## 1. Reviews Per Source\n"]
    
    for src, revs in by_source.items():
        md_content.append(f"- **{src}**: {len(revs)} reviews")
        
    md_content.append("\n---\n")
    
    for src, revs in by_source.items():
        md_content.append(f"## {src.capitalize()} Sample (Top 10)\n")
        sample = revs[:10]
        for i, r in enumerate(sample):
            md_content.append(f"### Review {i+1} (Status: `{r.get('status')}`)")
            text = r.get('raw_text', '').replace('\n', ' ')
            if len(text) > 300:
                text = text[:300] + '...'
            md_content.append(f"> {text}\n")
            
            # Fetch chunks and annotations
            chunks = supabase.table('review_chunks').select('id, chunk_text').eq('review_id', r['id']).execute().data
            if not chunks:
                md_content.append("- *No chunks extracted (filtered prior to extraction).*\n")
                continue
                
            md_content.append("**Extracted Annotations & Themes:**")
            for c in chunks:
                anns = supabase.table('chunk_annotations').select('decision_evidence_type, decision_driver').eq('chunk_id', c['id']).execute().data
                theme = chunk_to_theme.get(c['id'], 'None (Not synthesized)')
                
                if anns:
                    ann = anns[0]
                    etype = ann.get('decision_evidence_type')
                    driver = ann.get('decision_driver')
                    md_content.append(f"- `[{etype} : {driver}]` -> Theme: *{theme}*")
                else:
                    md_content.append(f"- *(No annotation)*")
            md_content.append("\n")
            
    out_path = r'C:\Users\ASUS\.gemini\antigravity-ide\brain\44382082-71f4-492d-af50-87a98a20593a\current_run_audit.md'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_content))
        
    print(f"Audit written to {out_path}")

if __name__ == '__main__':
    generate_audit()
