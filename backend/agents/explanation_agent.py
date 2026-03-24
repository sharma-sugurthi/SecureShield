"""
Explanation Agent — ReAct Tool-Calling Agent
Uses tools to generate patient-friendly explanations with actionable savings suggestions.

Tool Pipeline:
1. clause_explainer → explain each triggered rule in plain language
2. savings_calculator → find cost-saving alternatives
3. what_if_analyzer → run specific scenarios if high out-of-pocket
4. LLM (Gemini Flash) → generate empathetic, comprehensive explanation
"""

import json
import logging
import time
from agents.model_router import router
from models.verdict import Verdict, VerdictStatus, RuleMatchStatus
from tools.explanation_tools import clause_explainer, savings_calculator, what_if_analyzer
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an empathetic health insurance communication specialist working in India.

You have been provided with:
1. VERDICT: The deterministic eligibility verdict from the decision engine
2. CLAUSE_EXPLANATIONS: Plain-language explanations of each triggered policy rule
3. SAVINGS_ANALYSIS: Cost-saving alternatives calculated for the patient
4. POLICY DETAILS: Insurer and plan name

YOUR TASK: Generate a clear, empathetic explanation that:
1. Starts with the verdict in one clear sentence
2. Explains each rule that affected the claim, using the clause explanations provided
3. For PARTIALLY approved or DENIED claims, present the savings alternatives
4. Ends with 3-5 actionable, numbered suggestions

TONE: Warm, professional, no jargon. The patient may be stressed — be compassionate.
FORMAT: Use paragraphs, not technical bullet points. Amount in ₹ format.

Return ONLY a JSON object: {"explanation": "...", "suggestions": ["...", "..."]}"""


async def generate_explanation(
    verdict: Verdict,
    policy_name: str = "Unknown Plan",
    insurer: str = "Unknown Insurer",
    rules: list[dict] | None = None,
    original_facts: dict | None = None,
    sum_insured: float = 0,
) -> dict:
    """
    Full explanation pipeline with tool-calling:

    Step 1: [Tool] clause_explainer → explain each triggered rule
    Step 2: [Tool] savings_calculator → find savings (if claim is partial/denied)
    Step 3: [LLM] Generate empathetic explanation with all context
    
    Each step is audited.
    """
    pipeline_start = time.time()
    logger.info(f"[ExplanationAgent] ▶ Generating explanation for {verdict.overall_verdict.value} claim")

    # === Step 1: Explain each triggered clause ===
    t0 = time.time()
    clause_explanations = []
    for match in verdict.matched_rules:
        if match.status in (RuleMatchStatus.CAPPED, RuleMatchStatus.DENIED):
            explanation = clause_explainer(
                category=match.rule_category,
                clause_text=match.rule_condition,
                clause_ref=match.clause_reference,
            )
            explanation["impact"] = {
                "status": match.status.value,
                "claimed": match.claimed_amount,
                "eligible": match.eligible_amount,
                "shortfall": match.shortfall,
            }
            clause_explanations.append(explanation)
    t1 = time.time()

    audit_trail_logger(
        agent_name="ExplanationAgent", action="explain_clauses",
        input_summary=f"{len(verdict.matched_rules)} rules, {sum(1 for m in verdict.matched_rules if m.status in (RuleMatchStatus.CAPPED, RuleMatchStatus.DENIED))} triggered",
        output_summary=f"Generated {len(clause_explanations)} clause explanations",
        tools_used=["clause_explainer"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 2: Calculate savings (if not fully approved) ===
    savings_data = None
    if (verdict.overall_verdict != VerdictStatus.APPROVED 
            and rules and original_facts and sum_insured > 0):
        t0 = time.time()
        try:
            savings_data = savings_calculator(
                rules=rules,
                original_facts=original_facts,
                sum_insured=sum_insured,
            )
        except Exception as e:
            logger.warning(f"[ExplanationAgent] Savings calculation failed: {e}")
            savings_data = None
        t1 = time.time()

        audit_trail_logger(
            agent_name="ExplanationAgent", action="calculate_savings",
            input_summary=f"Verdict: {verdict.overall_verdict.value}, coverage: {verdict.coverage_percentage}%",
            output_summary=f"Found {len(savings_data.get('alternatives', []))} alternatives, "
                          f"max savings: ₹{savings_data.get('max_possible_savings', 0):,.0f}" if savings_data else "Savings calculation failed",
            tools_used=["savings_calculator", "what_if_analyzer"],
            duration_ms=(t1 - t0) * 1000,
        )

    # === Step 3: LLM — Generate empathetic explanation ===
    clause_text = json.dumps(clause_explanations, indent=2, default=str)[:4000]
    savings_text = json.dumps(savings_data, indent=2, default=str)[:2000] if savings_data else "No savings analysis available."

    user_prompt = f"""Generate a patient-friendly explanation for this insurance eligibility verdict.

VERDICT:
- Status: {verdict.overall_verdict.value}
- Total Claimed: ₹{verdict.total_claimed:,.0f}
- Eligible Amount: ₹{verdict.total_eligible:,.0f}
- Denied Amount: ₹{verdict.total_denied:,.0f}
- Coverage: {verdict.coverage_percentage}%
- Summary: {verdict.summary}

POLICY: {insurer} — {policy_name}

CLAUSE EXPLANATIONS (from clause_explainer tool):
{clause_text}

COST-SAVING ALTERNATIVES (from savings_calculator tool):
{savings_text}

Remember: Be empathetic and clear. Present savings alternatives as helpful suggestions, not criticism."""

    t0 = time.time()
    try:
        result = await router.call_json(
            role="explanation",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )
        explanation = result.get("explanation", verdict.summary)
        suggestions = result.get("suggestions", [])
    except Exception as e:
        logger.error(f"[ExplanationAgent] LLM generation failed: {e}, using fallback")
        explanation, suggestions = _generate_fallback(verdict, clause_explanations, savings_data)
    t1 = time.time()

    audit_trail_logger(
        agent_name="ExplanationAgent", action="generate_explanation",
        input_summary=f"Verdict: {verdict.overall_verdict.value}, {len(clause_explanations)} clauses",
        output_summary=f"Generated {len(explanation)} char explanation with {len(suggestions)} suggestions",
        tools_used=["model_router.call_json(explanation)"],
        duration_ms=(t1 - t0) * 1000,
    )

    pipeline_end = time.time()
    total_ms = (pipeline_end - pipeline_start) * 1000

    audit_trail_logger(
        agent_name="ExplanationAgent", action="pipeline_complete",
        input_summary=f"Verdict: {verdict.overall_verdict.value}",
        output_summary=f"Explanation ready: {len(explanation)} chars, {len(suggestions)} suggestions",
        tools_used=["clause_explainer", "savings_calculator", "model_router"],
        duration_ms=total_ms,
    )

    logger.info(f"[ExplanationAgent] ✓ Pipeline complete in {total_ms:.0f}ms")
    return {"explanation": explanation, "suggestions": suggestions}


def _generate_fallback(
    verdict: Verdict,
    clause_explanations: list[dict],
    savings_data: dict | None,
) -> tuple[str, list[str]]:
    """Generate explanation without LLM if it fails."""
    parts = [verdict.summary, ""]

    for ce in clause_explanations[:5]:
        parts.append(f"• {ce['simple_explanation']}")
        if ce.get("impact", {}).get("shortfall", 0) > 0:
            parts.append(f"  Impact: ₹{ce['impact']['shortfall']:,.0f} deducted.")
        parts.append(f"  💡 Tip: {ce['tip']}")
        parts.append("")

    if savings_data and savings_data.get("alternatives"):
        parts.append("💡 Ways to reduce your out-of-pocket costs:")
        for alt in savings_data["alternatives"][:3]:
            parts.append(f"  • {alt['change']} — could save ₹{alt['savings']:,.0f}")

    explanation = "\n".join(parts)

    suggestions = [
        "Request an itemized bill from the hospital for better claim processing.",
        "Contact your insurer's claim helpline for pre-authorization guidance.",
        "Keep all original medical reports, prescriptions, and receipts.",
    ]

    if savings_data and savings_data.get("alternatives"):
        for alt in savings_data["alternatives"][:2]:
            suggestions.append(f"Consider: {alt['change']} to save ₹{alt['savings']:,.0f}")

    return explanation, suggestions
