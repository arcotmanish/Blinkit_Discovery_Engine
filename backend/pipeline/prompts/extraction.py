"""
Decision Evidence Extraction Prompt — Stage 3

Extracts structured behavioral annotations from review chunks.
Batching: 2 chunks per LLM call.
"""

EXTRACTION_PROMPT = """You are a product researcher analyzing customer reviews for a quick-commerce app.

Your task is to first create a neutral structured observation describing what the customer explicitly reveals, and only afterwards classify that observation into the predefined taxonomy.

You are studying how customers make purchasing decisions — specifically 
what they buy repeatedly, what they avoid, and what drives those choices.

For each chunk below, extract the requested fields.

{chunks_block}

Instructions:
- Base ALL labels ONLY on what is explicitly stated in the text
- Do NOT infer demographics (age, income, location) if not stated
- If a field is unclear, use "none" — do not guess
- evidence_quote MUST be verbatim text from the excerpt above
- other_signal: use this for any behavioral observation not covered by the fields below

Return ONLY valid JSON. No markdown. No explanation. Return an array of {n} objects in the exact same order as the chunks:

[
  {{
    "customer_decision_observation":
        // Neutral description of what the customer explicitly reveals. Do not interpret beyond the text.
        "",
    "decision_evidence_type": 
        // MUST be one of: "repeat_purchase" | "category_avoidance" | 
        // "category_exploration" | "exploration_abandoned" | 
        // "switching_behavior" | "competitor_comparison" | 
        // "impulse_consideration" | "habitual_reorder" | "none"
        "none",
    "decision_driver":
        // MUST be one of: "trust" | "quality_uncertainty" | "awareness" | 
        // "habit" | "convenience" | "urgency" | "availability" | 
        // "price_sensitivity" | "recommendation" | "promotion" | 
        // "navigation_difficulty" | "past_experience" | "none"
        "none",
    "purchase_context":
        // MUST be one of: "weekly_routine" | "emergency_need" | "late_night" |
        // "family_household" | "health_wellness" | "festival_occasion" |
        // "gifting" | "office_work" | "routine_replenishment" | 
        // "exploration_mindset" | "none"
        "none",
    "categories_mentioned":
        // List of product categories explicitly mentioned. [] if none.
        [],
    "inferred_segment":
        // MUST be one of: "habitual_buyer" | "reluctant_explorer" | 
        // "trust_gated_shopper" | "prompt_dependent_buyer" | 
        // "dissatisfied_defector" | "unclassified"
        "unclassified",
    "evidence_quote":
        // 1-3 sentence verbatim extract directly supporting labels. null if none.
        null,
    "other_signal":
        // Any behavioral observation NOT captured above. null if none.
        null,
    "confidence":
        // MUST be one of: "high" | "medium" | "low"
        "low"
  }}
]
"""

def build_extraction_prompt(chunks: list) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(
            f"CHUNK {i}:\n"
            f"SOURCE: {c.get('source', 'unknown')} | RATING: {c.get('rating', 'N/A')}/5 | DATE: {c.get('date', 'unknown')}\n"
            f"EXCERPT:\n\"\"\"\n{c.get('text', '')}\n\"\"\""
        )
    chunks_block = "\n\n".join(lines)
    return EXTRACTION_PROMPT.format(chunks_block=chunks_block, n=len(chunks))
