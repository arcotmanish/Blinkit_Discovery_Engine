"""
Signal Scoring Prompt Template — Stage 2

Verbatim from AI_DISCOVERY_ENGINE_ARCHITECTURE.md Section 13.2.
Do NOT modify this prompt without updating the architecture document.
"""

SIGNAL_SCORING_PROMPT = """You are a behavioral research analyst studying customer purchasing decisions.

Your task is to assess whether this customer review contains meaningful \
evidence about HOW a customer makes purchasing decisions.

You are NOT looking for mentions of "discovery" or "new categories" specifically.
You ARE looking for any evidence of:
- What the customer buys repeatedly (or avoids)
- Why they make those decisions  
- What drives or prevents them from trying different things
- How they compare options or platforms
- What context shapes their purchasing

REVIEWS TO SCORE:
{reviews_block}

For EACH review, score from 0.0 to 1.0:
0.0–0.2: Pure operational feedback (OTP, crashes, delivery partner, support)
0.2–0.4: Operational issue, unclear link to purchasing decisions
0.4–0.6: Indirectly related (mentions variety, selection, options briefly)
0.6–0.8: Clear behavioral signal about purchasing patterns or decisions
0.8–1.0: Explicit evidence about why customer does or does not explore categories

Return ONLY valid JSON. No explanation. No markdown. Return an array with exactly {n} objects, one per review, in the same order:
[
  {{
    "signal_score": 0.0,
    "rationale": "One sentence citing specific text from the review that explains this score."
  }}
]"""


def build_scoring_prompt(reviews: list) -> str:
    """
    Build the scoring prompt for a batch of reviews.
    Each review is a dict with keys: id, text, source, rating, date
    """
    lines = []
    for i, r in enumerate(reviews, 1):
        lines.append(
            f"REVIEW {i}:\n"
            f"SOURCE: {r.get('source', 'unknown')}\n"
            f"RATING: {r.get('rating', 'N/A')}/5\n"
            f"DATE: {r.get('date', 'unknown')}\n"
            f"\"\"\"\n{r.get('text', '')}\n\"\"\""
        )
    reviews_block = "\n\n".join(lines)
    return SIGNAL_SCORING_PROMPT.format(
        reviews_block=reviews_block,
        n=len(reviews)
    )
