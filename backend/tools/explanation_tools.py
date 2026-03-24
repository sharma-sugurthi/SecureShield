"""
Explanation Tools — Custom tools for the Explanation Agent.

Tools:
9.  what_if_analyzer — Run decision engine with modified parameters
10. savings_calculator — Calculate savings from alternative choices
11. clause_explainer — Explain policy clauses in plain language
"""

import logging
import copy
from engine.decision_engine import evaluate
from models.case import CaseFacts, RoomType
from models.verdict import Verdict
from tools.case_tools import hospital_cost_estimator

logger = logging.getLogger(__name__)


# --- Tool 9: What-If Analyzer ---

_ROOM_DOWNGRADE_MAP = {
    "suite": "deluxe",
    "deluxe": "single_ac",
    "single_ac": "private",
    "private": "semi_private",
    "semi_private": "general",
    "icu": "icu",  # Can't downgrade ICU
    "general": "general",  # Already lowest
}

# Approximate room costs per tier for what-if estimation
_ROOM_COST_ESTIMATES = {
    "general": {"tier_1": 1500, "tier_2": 800, "tier_3": 500},
    "semi_private": {"tier_1": 4000, "tier_2": 2500, "tier_3": 1500},
    "private": {"tier_1": 8000, "tier_2": 5000, "tier_3": 3000},
    "single_ac": {"tier_1": 10000, "tier_2": 6000, "tier_3": 4000},
    "deluxe": {"tier_1": 18000, "tier_2": 12000, "tier_3": 8000},
    "suite": {"tier_1": 30000, "tier_2": 20000, "tier_3": 15000},
    "icu": {"tier_1": 25000, "tier_2": 15000, "tier_3": 8000},
}


def what_if_analyzer(
    rules: list[dict],
    original_facts: dict,
    sum_insured: float,
    modification: dict,
) -> dict:
    """
    Run decision engine with modified case parameters and compare results.
    
    Args:
        rules: Policy rules
        original_facts: Original case facts as dict
        sum_insured: Policy sum insured
        modification: Dict of field → new value changes to apply
    
    Returns:
        {
            "original_verdict": {eligible, denied, coverage},
            "modified_verdict": {eligible, denied, coverage},
            "savings": float (positive = patient saves money),
            "changes_applied": dict,
            "recommendation": str
        }
    """
    # Run original
    original_case = CaseFacts(**original_facts)
    original_verdict = evaluate(rules, original_case, sum_insured)

    # Apply modifications
    modified_data = copy.deepcopy(original_facts)
    for field, value in modification.items():
        if field in modified_data:
            modified_data[field] = value

    # Recalculate total if room cost or stay changed
    if "room_cost_per_day" in modification or "stay_duration_days" in modification:
        room_cost = float(modified_data.get("room_cost_per_day", 0))
        stay = int(modified_data.get("stay_duration_days", 1))
        proc_cost = float(modified_data.get("procedure_cost", 0) or 0)
        modified_data["total_claimed_amount"] = (room_cost * stay) + proc_cost

    modified_case = CaseFacts(**modified_data)
    modified_verdict = evaluate(rules, modified_case, sum_insured)

    savings = modified_verdict.total_eligible - original_verdict.total_eligible
    savings_out_of_pocket = original_verdict.total_denied - modified_verdict.total_denied

    # Generate recommendation
    if savings_out_of_pocket > 0:
        recommendation = (
            f"This change would reduce your out-of-pocket expense by ₹{savings_out_of_pocket:,.0f}. "
            f"Coverage improves from {original_verdict.coverage_percentage}% to {modified_verdict.coverage_percentage}%."
        )
    elif savings_out_of_pocket == 0:
        recommendation = "This change would not affect your out-of-pocket expenses."
    else:
        recommendation = (
            f"This change would increase your out-of-pocket expense by ₹{abs(savings_out_of_pocket):,.0f}."
        )

    logger.info(f"[Tool:what_if_analyzer] Original: {original_verdict.coverage_percentage}% → "
                f"Modified: {modified_verdict.coverage_percentage}%, Savings: ₹{savings_out_of_pocket:,.0f}")

    return {
        "original_verdict": {
            "eligible": original_verdict.total_eligible,
            "denied": original_verdict.total_denied,
            "coverage_pct": original_verdict.coverage_percentage,
        },
        "modified_verdict": {
            "eligible": modified_verdict.total_eligible,
            "denied": modified_verdict.total_denied,
            "coverage_pct": modified_verdict.coverage_percentage,
        },
        "savings_out_of_pocket": savings_out_of_pocket,
        "changes_applied": modification,
        "recommendation": recommendation,
    }


# --- Tool 10: Savings Calculator ---

def savings_calculator(
    rules: list[dict],
    original_facts: dict,
    sum_insured: float,
) -> dict:
    """
    Automatically calculate potential savings by exploring common alternatives:
    1. Room downgrade (one level down)
    2. Switch to network hospital
    3. Both combined
    
    Args:
        rules: Policy rules
        original_facts: Original case facts
        sum_insured: Policy sum insured
    
    Returns:
        {
            "alternatives": [
                {"change": str, "savings": float, "new_coverage": float, "details": str}
            ],
            "max_possible_savings": float,
            "best_alternative": str
        }
    """
    original_case = CaseFacts(**original_facts)
    original_verdict = evaluate(rules, original_case, sum_insured)
    
    alternatives = []
    
    # Alternative 1: Room downgrade
    current_room = original_facts.get("room_type", "single_ac")
    lower_room = _ROOM_DOWNGRADE_MAP.get(current_room, current_room)
    
    if lower_room != current_room:
        city_tier = original_facts.get("city_tier", "tier_1")
        new_room_cost = _ROOM_COST_ESTIMATES.get(lower_room, {}).get(city_tier, original_facts.get("room_cost_per_day", 0))
        
        room_result = what_if_analyzer(
            rules, original_facts, sum_insured,
            {
                "room_type": lower_room,
                "room_cost_per_day": new_room_cost,
            }
        )
        
        if room_result["savings_out_of_pocket"] > 0:
            alternatives.append({
                "change": f"Switch from {current_room.replace('_', ' ')} to {lower_room.replace('_', ' ')}",
                "savings": room_result["savings_out_of_pocket"],
                "new_coverage": room_result["modified_verdict"]["coverage_pct"],
                "new_room_cost_per_day": new_room_cost,
                "details": room_result["recommendation"],
            })

    # Alternative 2: Reduce stay by 1 day (if applicable)
    stay = int(original_facts.get("stay_duration_days", 1))
    if stay > 2:
        stay_result = what_if_analyzer(
            rules, original_facts, sum_insured,
            {"stay_duration_days": stay - 1}
        )
        if stay_result["savings_out_of_pocket"] > 0:
            alternatives.append({
                "change": f"Reduce stay from {stay} to {stay - 1} days (if medically possible)",
                "savings": stay_result["savings_out_of_pocket"],
                "new_coverage": stay_result["modified_verdict"]["coverage_pct"],
                "details": stay_result["recommendation"],
            })

    # Sort by savings
    alternatives.sort(key=lambda x: x["savings"], reverse=True)
    
    max_savings = alternatives[0]["savings"] if alternatives else 0
    best = alternatives[0]["change"] if alternatives else "No cost-saving alternatives found"

    logger.info(f"[Tool:savings_calculator] Found {len(alternatives)} alternatives, max savings: ₹{max_savings:,.0f}")
    
    return {
        "alternatives": alternatives,
        "max_possible_savings": max_savings,
        "best_alternative": best,
        "original_out_of_pocket": original_verdict.total_denied,
    }


# --- Tool 11: Clause Explainer ---

_CATEGORY_EXPLANATIONS = {
    "room_rent": {
        "simple": "This rule limits how much the insurance will pay for your hospital room per day.",
        "example": "If your room costs ₹10,000/day but the policy cap is ₹5,000/day, "
                   "you pay the extra ₹5,000/day from your pocket.",
        "tip": "Choose a room within the policy limit to avoid out-of-pocket costs.",
    },
    "copay": {
        "simple": "Co-payment means you share a percentage of the total bill with the insurance company.",
        "example": "With 20% co-pay on a ₹1,00,000 bill, insurance pays ₹80,000 and you pay ₹20,000.",
        "tip": "If your policy has voluntary co-pay, removing it increases premium but eliminates co-pay deductions.",
    },
    "sublimit": {
        "simple": "A sub-limit caps the maximum amount payable for a specific treatment or item.",
        "example": "If cataract surgery has a ₹40,000 sub-limit but the actual cost is ₹60,000, "
                   "you pay the extra ₹20,000.",
        "tip": "Check sub-limits for your specific procedure before choosing a hospital.",
    },
    "exclusion_permanent": {
        "simple": "This procedure/condition is not covered at all under your policy.",
        "example": "Cosmetic surgery is typically excluded. If you get rhinoplasty for cosmetic reasons, "
                   "insurance won't pay anything.",
        "tip": "Check if there's a medical necessity exception — some exclusions don't apply if "
               "the treatment is medically required (e.g., reconstructive surgery after an accident).",
    },
    "waiting_period_initial": {
        "simple": "You cannot make claims during the first 30 days of your policy (except for accidents).",
        "example": "If you buy insurance on January 1 and need planned surgery on January 15, it won't be covered.",
        "tip": "Emergency and accident-related hospitalization is covered from day 1.",
    },
    "waiting_period_specific": {
        "simple": "Certain diseases/procedures have a mandatory waiting period (usually 2-4 years) "
                  "before they're covered.",
        "example": "Knee replacement typically has a 24-month wait. If your policy is 6 months old, "
                   "this surgery isn't covered yet.",
        "tip": "Keep your policy continuously renewed — waiting periods are served only once.",
    },
    "waiting_period_pec": {
        "simple": "Pre-existing diseases (conditions you had before buying insurance) "
                  "are covered only after 2-4 years.",
        "example": "If you have diabetes when you buy insurance, diabetes-related hospitalization "
                   "won't be covered for 36-48 months.",
        "tip": "After 8 years of continuous coverage, the insurer cannot deny any claim citing pre-existing disease.",
    },
    "deductible": {
        "simple": "A deductible is a fixed amount you must pay before insurance kicks in.",
        "example": "With a ₹10,000 deductible on a ₹50,000 bill, you pay ₹10,000 and insurance pays ₹40,000.",
        "tip": "Higher deductible = lower premium. Choose based on your financial comfort.",
    },
}


def clause_explainer(category: str, clause_text: str = "", clause_ref: str = "") -> dict:
    """
    Explain a policy clause in simple, patient-friendly language.
    
    Args:
        category: Rule category (room_rent, copay, exclusion_permanent, etc.)
        clause_text: The original clause text from the policy
        clause_ref: Clause reference number
    
    Returns:
        {
            "category": str,
            "simple_explanation": str,
            "example": str,
            "tip": str,
            "original_clause": str,
            "clause_reference": str
        }
    """
    # Find the best matching explanation
    explanation = _CATEGORY_EXPLANATIONS.get(category)
    
    if not explanation:
        # Try to match partial category names
        for key, exp in _CATEGORY_EXPLANATIONS.items():
            if key in category or category in key:
                explanation = exp
                break

    if not explanation:
        explanation = {
            "simple": f"This rule ({category}) affects how your claim is processed.",
            "example": "Please refer to your policy document for specific details.",
            "tip": "Contact your insurer's customer service for clarification on this clause.",
        }

    return {
        "category": category,
        "simple_explanation": explanation["simple"],
        "example": explanation["example"],
        "tip": explanation["tip"],
        "original_clause": clause_text,
        "clause_reference": clause_ref,
    }
