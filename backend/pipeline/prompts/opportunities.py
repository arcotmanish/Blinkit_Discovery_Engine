"""
Phase 6b: Opportunity Generation Prompt
"""

OPPORTUNITY_PROMPT = """You are a senior product manager synthesizing research findings into 
actionable product opportunities.

BUSINESS OBJECTIVE:
Increase the percentage of Monthly Active Customers who purchase from 
at least one new category every month.

RESEARCH FINDINGS ({insight_count} strategic behavioral insights):
{formatted_insight_summaries}

Generate 3–5 prioritized product opportunities.

Each opportunity should:
1. Address a specific behavioral pattern from the research
2. Be directly derivable from customer evidence
3. Reference the COM-B lever it activates
4. Be specific enough for a product team to begin scoping

DO NOT:
- Generate generic UX recommendations
- Introduce problems not present in the research findings
- Duplicate opportunities that address the same root behavior

Return ONLY valid JSON:

{{
  "opportunities": [
    {{
      "title": "",
      "problem_statement": "",
      "evidence_summary": "",
      "product_direction": "",
      "com_b_lever": "capability",
      "parent_insight_references": [],
      "priority_rank": 1
    }}
  ]
}}
"""

def build_opportunity_prompt(insights: list) -> str:
    lines = []
    for i in insights:
        lines.append(
            f"INSIGHT: {i['title']}\n"
            f"TYPE: {i['insight_type']} | SCORE: {i.get('opportunity_score', 3)}/5\n"
            f"EVIDENCE COUNT: {i['evidence_count']}\n"
            f"DESCRIPTION: {i['description']}\n"
            f"HYPOTHESIS: {i['hypothesis']}\n"
            f"INTERVENTION HINT: {i.get('intervention_hint', 'N/A')}\n"
        )
    formatted = "\n\n".join(lines)
    return OPPORTUNITY_PROMPT.format(
        insight_count=len(insights),
        formatted_insight_summaries=formatted
    )
