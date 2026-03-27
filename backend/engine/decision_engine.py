"""
Deterministic Decision Engine
Applies frozen policy rules against case facts to produce an auditable verdict.
NO LLM calls — fully deterministic, zero hallucination risk.
"""

import logging
from models.policy import PolicyRule, LimitType
from models.case import CaseFacts
from models.verdict import Verdict, RuleMatch, VerdictStatus, RuleMatchStatus

logger = logging.getLogger(__name__)


def _apply_room_rent_rule(rule: PolicyRule, facts: CaseFacts, sum_insured: float) -> RuleMatch:
    """Apply a room rent cap rule."""
    room_total = facts.room_cost_per_day * facts.stay_duration_days

    if rule.limit_type == LimitType.PERCENTAGE:
        # e.g., "1% of sum insured per day"
        max_per_day = (rule.limit_value / 100) * sum_insured
        eligible_per_day = min(facts.room_cost_per_day, max_per_day)
        eligible_total = eligible_per_day * facts.stay_duration_days
    elif rule.limit_type == LimitType.ABSOLUTE:
        # e.g., "₹5000 per day"
        max_per_day = rule.limit_value or facts.room_cost_per_day
        eligible_per_day = min(facts.room_cost_per_day, max_per_day)
        eligible_total = eligible_per_day * facts.stay_duration_days
    else:
        max_per_day = facts.room_cost_per_day  # No cap — full amount eligible
        eligible_total = room_total

    shortfall = max(0, room_total - eligible_total)
    status = RuleMatchStatus.PASSED if shortfall == 0 else RuleMatchStatus.CAPPED

    return RuleMatch(
        rule_category="room_rent",
        rule_condition=rule.condition,
        status=status,
        claimed_amount=room_total,
        eligible_amount=eligible_total,
        shortfall=shortfall,
        clause_reference=rule.clause_reference,
        reason=f"Room rent {'within' if shortfall == 0 else 'exceeds'} policy limit of ₹{max_per_day:.0f}/day" if rule.limit_type != LimitType.PERCENTAGE else f"Room rent {'within' if shortfall == 0 else 'exceeds'} {rule.limit_value}% of SI (₹{max_per_day:.0f}/day)"
    )


def _apply_copay_rule(rule: PolicyRule, facts: CaseFacts, current_eligible: float) -> RuleMatch:
    """Apply a co-payment rule."""
    copay_pct = rule.limit_value or 0

    # Check if copay applies based on conditions
    applies = True
    applies_to = (rule.applies_to or "").lower()

    if "age" in applies_to:
        # Age-based copay (e.g., "20% copay for age > 60")
        if facts.patient_age and facts.patient_age < 60:
            applies = False

    if not applies:
        return RuleMatch(
            rule_category="copay",
            rule_condition=rule.condition,
            status=RuleMatchStatus.NOT_APPLICABLE,
            claimed_amount=current_eligible,
            eligible_amount=current_eligible,
            shortfall=0,
            clause_reference=rule.clause_reference,
            reason="Co-pay condition does not apply to this case"
        )

    copay_amount = (copay_pct / 100) * current_eligible
    eligible_after_copay = current_eligible - copay_amount

    return RuleMatch(
        rule_category="copay",
        rule_condition=rule.condition,
        status=RuleMatchStatus.CAPPED,
        claimed_amount=current_eligible,
        eligible_amount=eligible_after_copay,
        shortfall=copay_amount,
        clause_reference=rule.clause_reference,
        reason=f"Co-payment of {copay_pct}% applied: patient pays ₹{copay_amount:.0f}"
    )


def _apply_sublimit_rule(rule: PolicyRule, facts: CaseFacts, sum_insured: float) -> RuleMatch:
    """Apply a sub-limit rule (e.g., ICU charges, ambulance, etc.)."""
    # Determine the claimed amount for this category
    claimed = facts.total_claimed_amount  # Default to total

    if rule.limit_type == LimitType.PERCENTAGE:
        max_allowed = (rule.limit_value / 100) * sum_insured
    elif rule.limit_type == LimitType.ABSOLUTE:
        max_allowed = rule.limit_value or claimed
    else:
        max_allowed = claimed

    eligible = min(claimed, max_allowed)
    shortfall = max(0, claimed - eligible)

    if shortfall == 0:
        status = RuleMatchStatus.PASSED
        reason = f"Within sub-limit of ₹{max_allowed:.0f}"
    else:
        status = RuleMatchStatus.CAPPED
        reason = f"Exceeds sub-limit of ₹{max_allowed:.0f} by ₹{shortfall:.0f}"

    return RuleMatch(
        rule_category=rule.category,
        rule_condition=rule.condition,
        status=status,
        claimed_amount=claimed,
        eligible_amount=eligible,
        shortfall=shortfall,
        clause_reference=rule.clause_reference,
        reason=reason,
    )


def _apply_exclusion_rule(rule: PolicyRule, facts: CaseFacts) -> RuleMatch:
    """Check if the case falls under an exclusion."""
    # --- IRDAI 2024 Compliance: Moratorium Period ---
    # After 5 continuous years (60 months) of coverage, PED exclusions generally cannot be invoked (IRDAI 2024).
    if facts.policy_tenure_years >= 5:
        condition_lower = (rule.condition or "").lower()
        if "pre-existing" in condition_lower or "ped" in condition_lower or "waiting period" in condition_lower:
            audit_trail_logger("decision_engine", "moratorium_waive", 
                               {"tenure": facts.policy_tenure_years, "clause": rule.clause_reference})
            return RuleMatch(
                rule_category="exclusion",
                rule_condition=rule.condition,
                status=RuleMatchStatus.PASSED,
                claimed_amount=facts.total_claimed_amount,
                eligible_amount=facts.total_claimed_amount,
                shortfall=0,
                clause_reference=rule.clause_reference,
                reason="IRDAI 2024 Moratorium Period (5+ years) applies: Waiver of PED/Exclusions due to long-term tenure."
            )

    excluded = False
    reason = "Not excluded"

    applies_to = (rule.applies_to or "").lower()
    procedure_lower = facts.procedure.lower()

    # Check if the procedure matches the exclusion
    if applies_to and applies_to != "all":
        if applies_to in procedure_lower or procedure_lower in applies_to:
            excluded = True
            reason = f"Procedure '{facts.procedure}' is excluded under {rule.clause_reference}"

    # Check pre-existing condition exclusions
    if "pre_existing" in rule.category or "pre-existing" in rule.condition.lower():
        if facts.pre_existing_conditions:
            for condition in facts.pre_existing_conditions:
                if condition.lower() in (rule.applies_to or "").lower():
                    excluded = True
                    reason = f"Pre-existing condition '{condition}' — {rule.condition}"
                    break

    if excluded:
        return RuleMatch(
            rule_category="exclusion",
            rule_condition=rule.condition,
            status=RuleMatchStatus.DENIED,
            claimed_amount=facts.total_claimed_amount,
            eligible_amount=0,
            shortfall=facts.total_claimed_amount,
            clause_reference=rule.clause_reference,
            reason=reason,
        )

    return RuleMatch(
        rule_category="exclusion",
        rule_condition=rule.condition,
        status=RuleMatchStatus.NOT_APPLICABLE,
        claimed_amount=facts.total_claimed_amount,
        eligible_amount=facts.total_claimed_amount,
        shortfall=0,
        clause_reference=rule.clause_reference,
        reason="Exclusion does not apply to this case",
    )


def _apply_waiting_period_rule(rule: PolicyRule, facts: CaseFacts) -> RuleMatch:
    """Check waiting period rules with IRDAI 2024 compliance."""
    if not facts.policy_start_date:
        return RuleMatch(
            rule_category="waiting_period",
            rule_condition=rule.condition,
            status=RuleMatchStatus.NOT_APPLICABLE,
            claimed_amount=facts.total_claimed_amount,
            eligible_amount=facts.total_claimed_amount,
            shortfall=0,
            clause_reference=rule.clause_reference,
            reason="Policy start date not provided — cannot evaluate waiting period"
        )

    # Basic logic: If procedure is Cataract/Joint/etc and tenure < limit, deny.
    # We estimate tenure based on policy_tenure_years or policy_start_date.
    wait_months = rule.limit_value or 24
    tenure_months = facts.policy_tenure_years * 12
    
    condition = (rule.condition or "").lower()
    procedure = (facts.procedure or "").lower()
    
    # Simple semantic match: if rule mentions procedure and tenure < limit
    is_applicable_procedure = any(word in procedure for word in condition.split())
    
    if is_applicable_procedure and tenure_months < wait_months:
        return RuleMatch(
            rule_category="waiting_period",
            rule_condition=rule.condition,
            status=RuleMatchStatus.DENIED,
            claimed_amount=facts.total_claimed_amount,
            eligible_amount=0,
            shortfall=facts.total_claimed_amount,
            clause_reference=rule.clause_reference,
            reason=f"Waiting period for '{rule.condition}' not net: {tenure_months}m tenure < {wait_months}m required."
        )

    return RuleMatch(
        rule_category="waiting_period",
        rule_condition=rule.condition,
        status=RuleMatchStatus.PASSED,
        claimed_amount=facts.total_claimed_amount,
        eligible_amount=facts.total_claimed_amount,
        shortfall=0,
        clause_reference=rule.clause_reference,
        reason=f"Waiting period check: {tenure_months}m tenure meets/exceeds requirements."
    )


def _apply_deductible_rule(rule: PolicyRule, facts: CaseFacts, current_eligible: float) -> RuleMatch:
    """Apply deductible amount."""
    deductible = rule.limit_value or 0
    eligible_after = max(0, current_eligible - deductible)
    actual_deducted = current_eligible - eligible_after

    if actual_deducted == 0:
        return RuleMatch(
            rule_category="deductible",
            rule_condition=rule.condition,
            status=RuleMatchStatus.NOT_APPLICABLE,
            claimed_amount=current_eligible,
            eligible_amount=current_eligible,
            shortfall=0,
            clause_reference=rule.clause_reference,
            reason="No deductible applied"
        )

    return RuleMatch(
        rule_category="deductible",
        rule_condition=rule.condition,
        status=RuleMatchStatus.CAPPED,
        claimed_amount=current_eligible,
        eligible_amount=eligible_after,
        shortfall=actual_deducted,
        clause_reference=rule.clause_reference,
        reason=f"Deductible of ₹{deductible:.0f} applied"
    )


def evaluate(rules: list[dict], facts: CaseFacts, sum_insured: float) -> Verdict:
    """
    DETERMINISTIC DECISION ENGINE
    
    Applies all policy rules against case facts in a defined order.
    No LLM calls — fully auditable and reproducible.
    
    Rule application order:
    1. Exclusions (if any apply, claim is denied entirely)
    2. Room rent caps
    3. Sub-limits
    4. Waiting periods
    5. Deductibles
    6. Co-payments (applied last, on the remaining eligible amount)
    
    Returns: Verdict with detailed rule-by-rule breakdown
    """
    logger.info(f"[DecisionEngine] Evaluating case: {facts.procedure}, ₹{facts.total_claimed_amount}")

    matched_rules: list[RuleMatch] = []
    current_eligible = facts.total_claimed_amount
    has_denial = False

    # Convert dict rules to PolicyRule objects
    policy_rules = []
    for r in rules:
        try:
            policy_rules.append(PolicyRule(**r))
        except Exception as e:
            logger.warning(f"[DecisionEngine] Skipping invalid rule: {e}")

    # --- Phase 1: Check exclusions first ---
    for rule in policy_rules:
        if rule.limit_type == LimitType.EXCLUSION or rule.category == "exclusion":
            match = _apply_exclusion_rule(rule, facts)
            matched_rules.append(match)
            if match.status == RuleMatchStatus.DENIED:
                has_denial = True
                current_eligible = 0
                break  # Full denial — stop processing

    if has_denial:
        return Verdict(
            overall_verdict=VerdictStatus.DENIED,
            total_claimed=facts.total_claimed_amount,
            total_eligible=0,
            total_denied=facts.total_claimed_amount,
            coverage_percentage=0.0,
            matched_rules=matched_rules,
            summary=f"Claim DENIED — {matched_rules[-1].reason}"
        )

    # --- Phase 2: Room rent caps ---
    for rule in policy_rules:
        if rule.category == "room_rent":
            match = _apply_room_rent_rule(rule, facts, sum_insured)
            matched_rules.append(match)
            if match.shortfall > 0:
                # Proportional deduction: if room rent is capped,
                # other charges may also be proportionally reduced
                current_eligible -= match.shortfall

    # --- Phase 3: Sub-limits ---
    for rule in policy_rules:
        if rule.limit_type == LimitType.SUBLIMIT or rule.category in ("sublimit", "icu", "ambulance", "daycare"):
            match = _apply_sublimit_rule(rule, facts, sum_insured)
            matched_rules.append(match)

    # --- Phase 4: Waiting periods ---
    for rule in policy_rules:
        if rule.limit_type == LimitType.WAITING_PERIOD or rule.category == "waiting_period":
            match = _apply_waiting_period_rule(rule, facts)
            matched_rules.append(match)

    # --- Phase 5: Deductibles ---
    for rule in policy_rules:
        if rule.limit_type == LimitType.DEDUCTIBLE or rule.category == "deductible":
            match = _apply_deductible_rule(rule, facts, current_eligible)
            matched_rules.append(match)
            current_eligible = match.eligible_amount

    # --- Phase 6: Co-payments (applied last) ---
    for rule in policy_rules:
        if rule.limit_type == LimitType.COPAY or rule.category == "copay":
            match = _apply_copay_rule(rule, facts, current_eligible)
            matched_rules.append(match)
            current_eligible = match.eligible_amount

    # Final calculations
    current_eligible = max(0, current_eligible)
    total_denied = facts.total_claimed_amount - current_eligible
    coverage_pct = (current_eligible / facts.total_claimed_amount * 100) if facts.total_claimed_amount > 0 else 0

    # Determine overall verdict
    if coverage_pct >= 95:
        overall = VerdictStatus.APPROVED
        summary = f"Claim APPROVED — ₹{current_eligible:,.0f} of ₹{facts.total_claimed_amount:,.0f} eligible ({coverage_pct:.0f}% coverage)"
    elif coverage_pct > 0:
        overall = VerdictStatus.PARTIAL
        summary = f"Claim PARTIALLY approved — ₹{current_eligible:,.0f} of ₹{facts.total_claimed_amount:,.0f} eligible ({coverage_pct:.0f}% coverage), ₹{total_denied:,.0f} denied"
    else:
        overall = VerdictStatus.DENIED
        summary = f"Claim DENIED — ₹{facts.total_claimed_amount:,.0f} not eligible"

    # Reliability Scoring (Claim Guardian Heuristic)
    confidence = 1.0
    if not is_reviewed:
        confidence -= 0.2  # Unreviewed policy extraction is risky
    
    # Analyze rule complexity for additional risk
    for rule in matched_rules:
        if rule.status == RuleMatchStatus.CAPPED:
            if rule.rule_category == "room_rent":
                confidence -= 0.1  # Proportional deduction complex bills
            else:
                confidence -= 0.05 # Other caps

    confidence = max(0.4, min(1.0, confidence))
    requires_review = confidence < 0.75

    verdict = Verdict(
        overall_verdict=overall,
        total_claimed=facts.total_claimed_amount,
        total_eligible=current_eligible,
        total_denied=total_denied,
        coverage_percentage=round(coverage_pct, 1),
        matched_rules=matched_rules,
        summary=summary,
        confidence_score=round(confidence, 2),
        requires_manual_review=requires_review
    )

    if requires_review:
        logger.warning(f"[DecisionEngine] Low confidence verdict ({confidence:.2f}) — Flagging for manual review")
        audit_trail_logger("decision_engine", "safety_gate_trigger", 
                           {"confidence": confidence, "reason": "Low confidence threshold reached"})

    logger.info(f"[DecisionEngine] Verdict: {overall.value} — {coverage_pct:.0f}% coverage (Confidence: {confidence:.2f})")
    return verdict
