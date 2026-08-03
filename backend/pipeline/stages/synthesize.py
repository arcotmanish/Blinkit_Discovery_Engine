"""
Stage 5: Final Synthesis
========================
Takes the quantitative scores from Stage 4 and the raw reviews from Stage 3,
and asks the LLM to synthesize answers for 8 core PM questions.

Includes a maximum of 2 retries on API failure, with delay.
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from supabase import create_client
from groq import Groq

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

client = Groq(api_key=os.environ["GROQ_API_KEY"])

QUESTIONS = [
    {"id": "q1", "text": "Why do users repeatedly buy from the same categories?"},
    {"id": "q2", "text": "What prevents users from exploring new categories?"},
    {"id": "q3", "text": "How do users discover products today?"},
    {"id": "q4", "text": "What role do habits play in shopping behavior?"},
    {"id": "q5", "text": "What information do users need before trying a new category?"},
    {"id": "q6", "text": "What frustrations emerge repeatedly?"},
    {"id": "q7", "text": "Which user segments are more likely to experiment?"},
    {"id": "q8", "text": "What unmet needs emerge consistently across discussions?"}
]

def fetch_all(table: str, columns: str = "*") -> list:
    all_data, page, size = [], 0, 1000
    while True:
        start = page * size
        resp = supabase.table(table).select(columns).range(start, start + size - 1).execute()
        data = resp.data or []
        all_data.extend(data)
        if len(data) < size:
            break
        page += 1
    return all_data

def get_synthesize_prompt(scores_json: str, chunks_text: str, question: str) -> str:
    return f"""You are a Principal Product Manager at Blinkit. Your goal is to analyze customer research data and provide deep, strategic insights. You will be given a statistical summary of recent app reviews, alongside the raw text of those reviews. Your task is to answer a specific product question using ONLY the provided data. Do not hallucinate external facts, features, or behaviors that are not present in the provided data.

Here is the Statistical Data from Stage 4: 
{scores_json}

Here are the Raw User Reviews:
{chunks_text}

**Question to Answer:** {question}

Read the data above and answer the question. You MUST respond in strict JSON format with exactly these three keys:

1. "answer_text": A 1-2 paragraph deep insight answering the question based strictly on the provided data. Focus on the 'Why' behind the customer behavior.
2. "key_statistic": A single metric from the Statistical Data (e.g. '42% of users...') that proves your point.
3. "supporting_quotes": A JSON array of exactly 3 distinct quotes copied exactly from the Raw User Reviews that perfectly illustrate your point.

Output raw JSON only. Do not include markdown formatting like ```json or any conversational text.
"""

def call_llm_with_retry(prompt: str, max_retries: int = 2) -> dict:
    """Calls Groq API with a maximum of 2 retries and strict JSON validation."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Validate required keys
            required_keys = {"answer_text", "key_statistic", "supporting_quotes"}
            if not required_keys.issubset(parsed.keys()):
                raise ValueError("LLM response is missing required JSON keys.")
                
            return parsed

        except Exception as e:
            err_msg = str(e)
            print(f"    [Error] Attempt {attempt + 1}/{max_retries} failed: {err_msg}")
            if attempt < max_retries - 1:
                print("    Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("    Max retries reached. Aborting this question.")
                return {"error": err_msg}

def main():
    print("\n[Stage 5] Synthesizing PM Reports...")
    
    # 1. Fetch Stage 4 Scores
    print("  Fetching signal scores...")
    scores = fetch_all("signal_scores")
    # Simplify scores for prompt
    simplified_scores = [
        {
            "signal_type": s["signal_type"],
            "key": s["signal_key"],
            "key2": s.get("signal_key2"),
            "count": s["count"],
            "percentage": s["percentage"]
        } for s in scores
    ]
    scores_json = json.dumps(simplified_scores, indent=2)
    
    import random
    
    # 2. Fetch Raw Quotes (Deduplicated & Sampled for Rate Limits)
    print("  Fetching raw chunks...")
    annotations = fetch_all("chunk_annotations")
    
    unique_chunks_dict = {a["chunk_id"]: a["evidence_quote"] for a in annotations if not a.get("annotation_failed")}
    all_unique_quotes = list(unique_chunks_dict.values())
    
    # Sample down to 30 to prevent Groq 12,000 TPM limit on free tier
    sampled_quotes = random.sample(all_unique_quotes, min(30, len(all_unique_quotes)))
    chunks_text = "\n".join([f"- {text}" for text in sampled_quotes])
    
    # Run ID to group this synthesis
    run_id = scores[0]["run_id"] if scores else "unknown"

    print(f"  Loaded {len(scores)} score metrics and {len(unique_chunks_dict)} unique review chunks.\n")
    
    # 3. Generate answers one by one
    for q in QUESTIONS:
        print(f"  Generating answer for: {q['text']}")
        prompt = get_synthesize_prompt(scores_json, chunks_text, q["text"])
        
        result = call_llm_with_retry(prompt, max_retries=2)
        
        if "error" in result:
            print(f"  Failed to generate report for {q['id']}. Skipping.")
            continue
            
        print("  Saving to database...")
        supabase.table("synthesized_reports").insert({
            "run_id": run_id,
            "question_id": q["id"],
            "question_text": q["text"],
            "answer_text": result["answer_text"],
            "key_statistic": result["key_statistic"],
            "supporting_quote": json.dumps(result["supporting_quotes"])
        }).execute()
        
        # Delay between successful questions to prevent rate limits
        print("  Waiting 12 seconds to respect free tier rate limits...")
        time.sleep(12)
        
    print("\n[Stage 5] Synthesis complete! Refresh your dashboard to see the insights.")

if __name__ == "__main__":
    main()
