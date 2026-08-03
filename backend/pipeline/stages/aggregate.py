"""
Stage 4: Aggregation & Merge (Phase 6)
"""
import sys
import os
import asyncio
from collections import Counter
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from db.client import supabase
from utils.llm import call_llm_async

MERGE_PROMPT = """
You are reviewing two behavioral clusters from customer research. Decide if they represent 
one unified behavioral phenomenon or two distinct behaviors with different product implications.

CLUSTER A: {cluster_key_A}
Evidence Type: {evidence_type_A} | Driver: {driver_A} | Evidence Count: {count_A}
Top categories: {categories_A}
Sample evidence (3 quotes): {quotes_A}

CLUSTER B: {cluster_key_B}  
Evidence Type: {evidence_type_B} | Driver: {driver_B} | Evidence Count: {count_B}
Top categories: {categories_B}
Sample evidence (3 quotes): {quotes_B}

Merge them ONLY if:
- They describe the same root customer behavior
- A PM reading both would have the same "what to build" response to both
- Keeping them separate would produce redundant themes

Return ONLY valid JSON:
{{"should_merge": true, "rationale": "One sentence explaining the decision."}}
"""

async def run_stage_4_aggregate(run_id: str):
    print(f"Starting Stage 4 (Aggregate) for run: {run_id}")
    
    total_res = supabase.table("chunk_annotations").select("chunk_id", count="exact").eq("run_id", run_id).execute()
    total_chunks_in_run = total_res.count if hasattr(total_res, 'count') and total_res.count else len(total_res.data)
    if not total_chunks_in_run:
        print("No chunks found in run.")
        return []
        
    print(f"  Total chunks in run: {total_chunks_in_run}")

    res = supabase.table("chunk_annotations").select(
        "id, chunk_id, decision_evidence_type, decision_driver, purchase_context, categories_mentioned, inferred_segment, evidence_quote, confidence, review_chunks(review_id, raw_reviews(source, rating))"
    ).eq("run_id", run_id).neq("decision_evidence_type", "none").in_("confidence", ["high", "medium"]).execute()
    
    annotations = res.data or []
    print(f"  Found {len(annotations)} eligible annotations for clustering.")
    
    clusters = {}
    for a in annotations:
        key = f"{a['decision_evidence_type']}:{a['decision_driver']}"
        if key not in clusters:
            clusters[key] = {
                "key": key,
                "evidence_type": a['decision_evidence_type'],
                "driver": a['decision_driver'],
                "chunks": [],
                "chunk_ids": [],
                "categories": Counter(),
                "segments": Counter(),
                "contexts": Counter(),
                "source_distribution": Counter(),
                "rating_distribution": Counter()
            }
        
        c = clusters[key]
        c["chunks"].append(a)
        c["chunk_ids"].append(a["chunk_id"])
        
        cats = a.get("categories_mentioned") or []
        if isinstance(cats, list):
            c["categories"].update(cats)
            
        c["segments"].update([a.get("inferred_segment", "unclassified")])
        c["contexts"].update([a.get("purchase_context", "none")])
        
        rc = a.get("review_chunks")
        if rc and isinstance(rc, dict):
            rr = rc.get("raw_reviews")
            if rr and isinstance(rr, dict):
                src = rr.get("source")
                if src:
                    c["source_distribution"].update([src])
                rating = rr.get("rating")
                if rating:
                    c["rating_distribution"].update([str(rating)])

    threshold = 8
    valid_clusters = [c for c in clusters.values() if len(c["chunks"]) >= threshold]
    
    if len(valid_clusters) < 5:
        threshold = 5
        valid_clusters = [c for c in clusters.values() if len(c["chunks"]) >= threshold]
        
    if len(valid_clusters) < 5:
        threshold = 3
        valid_clusters = [c for c in clusters.values() if len(c["chunks"]) >= threshold]
        
    print(f"  Adaptive threshold set to: {threshold} chunks")
    
    additional_signals = [c for c in clusters.values() if len(c["chunks"]) < threshold]
    print(f"  Found {len(valid_clusters)} valid clusters and {len(additional_signals)} additional signals.")
    
    valid_clusters.sort(key=lambda c: len(c["chunks"]), reverse=True)
    
    def get_adjacent(et):
        adj = {
            "repeat_purchase": ["habitual_reorder"],
            "habitual_reorder": ["repeat_purchase"],
            "category_exploration": ["impulse_consideration"],
            "impulse_consideration": ["category_exploration"]
        }
        return adj.get(et, [])
        
    def get_adjacent_driver(d):
        adj = {
            "trust": ["quality_uncertainty"],
            "quality_uncertainty": ["trust"]
        }
        return adj.get(d, [])

    merged = set()
    final_clusters = []
    
    for i in range(len(valid_clusters)):
        if i in merged: continue
        
        c1 = valid_clusters[i]
        
        for j in range(i+1, len(valid_clusters)):
            if j in merged: continue
            
            c2 = valid_clusters[j]
            
            nominate = False
            if c1["driver"] == c2["driver"] and c2["evidence_type"] in get_adjacent(c1["evidence_type"]):
                nominate = True
            elif c1["evidence_type"] == c2["evidence_type"] and c2["driver"] in get_adjacent_driver(c1["driver"]):
                nominate = True
            elif len(c1["chunks"]) < 12 and len(c2["chunks"]) < 12:
                nominate = True
                
            if nominate:
                print(f"    Nominating merge: {c1['key']} + {c2['key']}")
                prompt = MERGE_PROMPT.format(
                    cluster_key_A=c1["key"],
                    evidence_type_A=c1["evidence_type"],
                    driver_A=c1["driver"],
                    count_A=len(c1["chunks"]),
                    categories_A=[k for k,v in c1["categories"].most_common(3)],
                    quotes_A=[a["evidence_quote"] for a in c1["chunks"][:3] if a.get("evidence_quote")],
                    
                    cluster_key_B=c2["key"],
                    evidence_type_B=c2["evidence_type"],
                    driver_B=c2["driver"],
                    count_B=len(c2["chunks"]),
                    categories_B=[k for k,v in c2["categories"].most_common(3)],
                    quotes_B=[a["evidence_quote"] for a in c2["chunks"][:3] if a.get("evidence_quote")]
                )
                
                try:
                    decision = await call_llm_async(prompt)
                    if isinstance(decision, list) and len(decision) > 0:
                        decision = decision[0]
                    if decision.get("should_merge"):
                        print(f"      Merge APPROVED: {decision.get('rationale')}")
                        c1["chunks"].extend(c2["chunks"])
                        c1["chunk_ids"].extend(c2["chunk_ids"])
                        c1["categories"].update(c2["categories"])
                        c1["segments"].update(c2["segments"])
                        c1["contexts"].update(c2["contexts"])
                        c1["source_distribution"].update(c2["source_distribution"])
                        c1["rating_distribution"].update(c2["rating_distribution"])
                        merged.add(j)
                    else:
                        print(f"      Merge REJECTED: {decision.get('rationale')}")
                except Exception as e:
                    print(f"      Merge error: {e}")
                    
        final_clusters.append(c1)
        
    final_clusters.sort(key=lambda c: len(c["chunks"]), reverse=True)
    strategic_themes = final_clusters[:7]
    additional_signals.extend(final_clusters[7:])
    
    print(f"  Final clusters: {len(strategic_themes)} strategic themes, {len(additional_signals)} additional signals.")
    
    for c in strategic_themes:
        c["corpus_percentage"] = round((len(c["chunks"]) / total_chunks_in_run) * 100, 2) if total_chunks_in_run else 0
        c["is_strategic_theme"] = True
        
    for c in additional_signals:
        c["corpus_percentage"] = round((len(c["chunks"]) / total_chunks_in_run) * 100, 2) if total_chunks_in_run else 0
        c["is_strategic_theme"] = False

    return strategic_themes + additional_signals

if __name__ == '__main__':
    try:
        pending = supabase.table("raw_reviews").select("run_id").limit(1).execute()
        if pending.data:
            run_id = pending.data[0]['run_id']
            res = asyncio.run(run_stage_4_aggregate(run_id))
    except Exception as e:
        print(f"Error: {e}")
