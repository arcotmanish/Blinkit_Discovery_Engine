"""
Phase 6 Synthesis Prompt
"""

SYNTHESIS_PROMPT = """You are a senior product researcher presenting findings to a Product Manager.

You are synthesizing one strategic behavioral insight from customer evidence.

CLUSTER PROFILE:
  Behavior Type: {decision_evidence_type}
  Decision Driver: {decision_driver}
  Evidence Count: {chunk_count} customer excerpts
  Top Categories Mentioned: {top_categories}
  Top Customer Segments: {top_segments}
  Most Common Context: {top_contexts}

CUSTOMER EVIDENCE ({sample_size} representative excerpts):
{formatted_evidence_list}

Your task is to synthesize ONE strategic behavioral insight.

CRITICAL RULES:
1. Base your insight ONLY on the customer evidence provided above
2. Do NOT introduce general knowledge or assumptions
3. If the evidence is contradictory, DESCRIBE the contradiction — do not hide it
4. State the insight as a behavioral finding, not a topic label
5. The title should describe a behavior or mechanism, not a sentiment
6. If evidence spans unrelated product categories, synthesize the shared customer decision behavior rather than naming any specific product category unless that category clearly dominates the supporting evidence.

Return ONLY valid JSON. No markdown. No explanation:

{{
  "title": 
      // 6–12 word behavioral statement. 
      // BAD: "Trust Issues with Meat"
      // GOOD: "Quality uncertainty prevents first purchase in fresh categories"
      "",
  "description":
      // 2–3 sentences explaining the behavioral pattern in PM language.
      // Reference the evidence volume and customer language.
      "",
  "hypothesis":
      // A falsifiable behavioral hypothesis.
      // Format: "Customers who [segment/behavior] do not [action] because [specific reason]"
      "",
  "confidence": 
      // "high" | "medium" | "low"
      // Base on: consistency across excerpts + evidence volume + signal clarity
      "",
  "confidence_rationale":
      // One sentence explaining the confidence rating
      "",
  "opportunity_score":
      // Integer 1–5
      // 5 = high frequency + high severity + clear product lever exists
      // 1 = low frequency or ambiguous product implication
      3,
  "com_b_interpretation":
      // Post-hoc: which COM-B dimension does this pattern map to?
      // "capability" | "opportunity" | "motivation" | "mixed"
      // Explain briefly in one sentence.
      "",
  "intervention_hint":
      // One specific product direction derivable from what customers said.
      // Must reference specific customer language.
      // NOT generic advice like "improve the UX."
      "",
  "has_contradiction":
      // true if the evidence contains conflicting signals
      false,
  "contradiction_description":
      // If has_contradiction is true, describe the contradiction in 1–2 sentences.
      // Return null if no contradiction.
      null,
  "insight_type":
      // MUST be one of: "barrier" | "discovery_pattern" | "habit_pattern" | "unmet_need" | "switching_signal"
      "discovery_pattern",
  "suggested_interview_question":
      // One open-ended question a researcher would ask to probe this pattern
      // Format: "Tell me about a time when you [behavioral description]..."
      "",
  "suggested_survey_hypothesis":
      // A falsifiable survey statement for quantitative validation
      // Format: "[X]% of Blinkit users who [behavior] would [action] if [intervention]"
      ""
}}
"""

def build_synthesis_prompt(cluster: dict) -> str:
    chunks = cluster.get("chunks", [])
    quotes = [c["evidence_quote"] for c in chunks if c.get("evidence_quote")]
    
    sample = quotes[:10]
    formatted_evidence_list = "\n".join([f"- \"{q}\"" for q in sample])
    
    return SYNTHESIS_PROMPT.format(
        decision_evidence_type=cluster["evidence_type"],
        decision_driver=cluster["driver"],
        chunk_count=len(chunks),
        top_categories=", ".join([k for k,v in cluster["categories"].most_common(3)]),
        top_segments=", ".join([k for k,v in cluster["segments"].most_common(3)]),
        top_contexts=", ".join([k for k,v in cluster["contexts"].most_common(3)]),
        sample_size=len(sample),
        formatted_evidence_list=formatted_evidence_list
    )
