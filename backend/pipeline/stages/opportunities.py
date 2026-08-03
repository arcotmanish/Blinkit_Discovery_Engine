"""
Stage 6: Opportunity Generation (Phase 6b)
"""

import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.client import supabase
from utils.llm import call_llm_async
from pipeline.prompts.opportunities import build_opportunity_prompt

async def run_stage_6_opportunities(run_id: str):
    print(f"Starting Stage 6 (Opportunities) for run: {run_id}")
    
    res = supabase.table("synthesized_insights").select("*").eq("run_id", run_id).execute()
    insights = res.data or []
    
    if not insights:
        print("No insights found for opportunity generation.")
        return
        
    print(f"Generating opportunities from {len(insights)} insights...")
    prompt = build_opportunity_prompt(insights)
    
    try:
        result = await call_llm_async(prompt)
        opps = result.get("opportunities", [])
        print(f"  Generated {len(opps)} opportunities.")
        
        for opp in opps:
            payload = {
                "run_id": run_id,
                "title": opp.get("title", "Untitled"),
                "problem_statement": opp.get("problem_statement", ""),
                "evidence_summary": opp.get("evidence_summary", ""),
                "product_direction": opp.get("product_direction", ""),
                "com_b_lever": opp.get("com_b_lever", "capability"),
                "priority_rank": opp.get("priority_rank", 1)
            }
            try:
                supabase.table("opportunities").insert(payload).execute()
            except Exception as e:
                print(f"    Failed to save opportunity: {e}")
                
    except Exception as e:
        print(f"  [Opportunities] LLM error: {e}")
        
    print("Stage 6 complete.")

if __name__ == '__main__':
    try:
        pending = supabase.table("synthesized_insights").select("run_id").limit(1).execute()
        if pending.data:
            run_id = pending.data[0]['run_id']
            supabase.table("opportunities").delete().eq("run_id", run_id).execute()
            asyncio.run(run_stage_6_opportunities(run_id))
    except Exception as e:
        print(f"Error: {e}")
