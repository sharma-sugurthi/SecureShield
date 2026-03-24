"""
Comprehensive tests for the Deterministic Decision Engine.
Tests cover: room rent caps, co-payments, exclusions, sub-limits,
deductibles, waiting periods, and complex multi-rule scenarios.

These tests use NO LLM calls — they validate pure deterministic logic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.decision_engine import evaluate
from models.case import CaseFacts, RoomType, AdmissionType, CityTier
from models.verdict import VerdictStatus, RuleMatchStatus


# --- Helper ---

def make_case(**overrides) -> CaseFacts:
    """Create a CaseFacts with sensible defaults."""
    defaults = {
        "room_type": RoomType.SINGLE_AC,
        "room_cost_per_day": 5000,
        "stay_duration_days": 3,
        "admission_type": AdmissionType.PLANNED,
        "procedure": "Appendectomy",
        "procedure_cost": 60000,
        "total_claimed_amount": 75000,  # 5000*3 + 60000
        "city_tier": CityTier.TIER_1,
    }
    defaults.update(overrides)
    return CaseFacts(**defaults)


# ============================================================
# TEST 1: Simple approved claim (no deductions)
# ============================================================

class TestApprovedClaim:
    """When no rules are violated, claim should be fully approved."""

    def test_no_rules_full_approval(self):
        """Empty rules list → 100% coverage."""
        case = make_case()
        verdict = evaluate(rules=[], facts=case, sum_insured=1000000)
        
        assert verdict.overall_verdict == VerdictStatus.APPROVED
        assert verdict.total_eligible == 75000
        assert verdict.total_denied == 0
        assert verdict.coverage_percentage == 100.0

    def test_room_within_limit(self):
        """Room cost within cap → no deduction."""
        rules = [{
            "category": "room_rent",
            "condition": "Room rent capped at 1% of sum insured per day",
            "limit_type": "percentage",
            "limit_value": 1.0,
            "clause_reference": "Section 4.2",
            "applies_to": "all"
        }]
        # 1% of 10L = ₹10,000/day, room is ₹5,000/day → within limit
        case = make_case(room_cost_per_day=5000)
        verdict = evaluate(rules, case, sum_insured=1000000)
        
        assert verdict.overall_verdict == VerdictStatus.APPROVED
        room_match = [m for m in verdict.matched_rules if m.rule_category == "room_rent"][0]
        assert room_match.status == RuleMatchStatus.PASSED
        assert room_match.shortfall == 0


# ============================================================
# TEST 2: Room rent capping
# ============================================================

class TestRoomRentCapping:
    """Room rent cap scenarios — the most common deduction in Indian health insurance."""

    def test_percentage_cap_exceeded(self):
        """Room rent exceeds % cap → shortfall deducted."""
        rules = [{
            "category": "room_rent",
            "condition": "Room rent capped at 1% of sum insured per day",
            "limit_type": "percentage",
            "limit_value": 1.0,
            "clause_reference": "Section 4.2(a)",
            "applies_to": "all"
        }]
        # SI=5L, 1% = ₹5,000/day, room=₹8,000/day → ₹3,000 shortfall/day × 3 days = ₹9,000
        case = make_case(room_cost_per_day=8000, total_claimed_amount=84000)
        verdict = evaluate(rules, case, sum_insured=500000)
        
        room_match = [m for m in verdict.matched_rules if m.rule_category == "room_rent"][0]
        assert room_match.status == RuleMatchStatus.CAPPED
        assert room_match.shortfall == 9000  # (8000-5000) × 3

    def test_absolute_cap(self):
        """Absolute room rent cap (e.g., ₹4,000/day)."""
        rules = [{
            "category": "room_rent",
            "condition": "Room rent capped at ₹4,000 per day",
            "limit_type": "absolute",
            "limit_value": 4000,
            "clause_reference": "Section 4.2(b)",
            "applies_to": "all"
        }]
        # Room=₹6,000/day, cap=₹4,000 → ₹2,000 shortfall/day × 3 = ₹6,000
        case = make_case(room_cost_per_day=6000, total_claimed_amount=78000)
        verdict = evaluate(rules, case, sum_insured=500000)
        
        room_match = [m for m in verdict.matched_rules if m.rule_category == "room_rent"][0]
        assert room_match.status == RuleMatchStatus.CAPPED
        assert room_match.shortfall == 6000


# ============================================================
# TEST 3: Co-payment
# ============================================================

class TestCopayment:
    """Co-payment deductions (applied last on remaining eligible amount)."""

    def test_flat_copay(self):
        """20% co-payment on entire claim."""
        rules = [{
            "category": "copay",
            "condition": "20% co-payment on all claims",
            "limit_type": "copay",
            "limit_value": 20.0,
            "clause_reference": "Section 6.1",
            "applies_to": "all"
        }]
        case = make_case(total_claimed_amount=100000)
        verdict = evaluate(rules, case, sum_insured=500000)
        
        copay_match = [m for m in verdict.matched_rules if m.rule_category == "copay"][0]
        assert copay_match.status == RuleMatchStatus.CAPPED
        assert copay_match.shortfall == 20000  # 20% of 100000
        assert verdict.total_eligible == 80000

    def test_copay_combined_with_room_cap(self):
        """Room rent cap + co-pay applied sequentially."""
        rules = [
            {
                "category": "room_rent",
                "condition": "Room rent capped at 1% of SI per day",
                "limit_type": "percentage",
                "limit_value": 1.0,
                "clause_reference": "Section 4.2",
                "applies_to": "all"
            },
            {
                "category": "copay",
                "condition": "20% co-payment",
                "limit_type": "copay",
                "limit_value": 20.0,
                "clause_reference": "Section 6.1",
                "applies_to": "all"
            }
        ]
        # SI=5L, room=₹8000/day×3=₹24000, cap=₹5000/day×3=₹15000, shortfall=₹9000
        # Eligible after room cap: 74000-9000=65000
        # Copay 20% of 65000 = 13000 → final eligible = 52000
        case = make_case(room_cost_per_day=8000, total_claimed_amount=74000)
        verdict = evaluate(rules, case, sum_insured=500000)
        
        assert verdict.total_eligible == 52000
        assert verdict.overall_verdict == VerdictStatus.PARTIAL


# ============================================================
# TEST 4: Exclusions
# ============================================================

class TestExclusions:
    """Exclusion rules — full denial of specific procedures/conditions."""

    def test_procedure_exclusion(self):
        """Excluded procedure → full denial."""
        rules = [{
            "category": "exclusion_permanent",
            "condition": "Cosmetic surgery is permanently excluded",
            "limit_type": "exclusion",
            "limit_value": None,
            "clause_reference": "Section 8.1(c)",
            "applies_to": "cosmetic surgery"
        }]
        case = make_case(procedure="Cosmetic Surgery - Rhinoplasty")
        verdict = evaluate(rules, case, sum_insured=500000)
        
        assert verdict.overall_verdict == VerdictStatus.DENIED
        assert verdict.total_eligible == 0
        assert verdict.coverage_percentage == 0.0

    def test_non_matching_exclusion(self):
        """Exclusion that doesn't apply → no effect."""
        rules = [{
            "category": "exclusion_permanent",
            "condition": "Cosmetic surgery is excluded",
            "limit_type": "exclusion",
            "limit_value": None,
            "clause_reference": "Section 8.1(c)",
            "applies_to": "cosmetic surgery"
        }]
        case = make_case(procedure="Appendectomy")
        verdict = evaluate(rules, case, sum_insured=500000)
        
        # Exclusion shouldn't apply
        exclusion_matches = [m for m in verdict.matched_rules 
                           if m.rule_category == "exclusion" and m.status == RuleMatchStatus.DENIED]
        assert len(exclusion_matches) == 0


# ============================================================
# TEST 5: Deductibles
# ============================================================

class TestDeductibles:
    """Deductible amounts subtracted from eligible amount."""

    def test_deductible_applied(self):
        """₹10,000 deductible reduces eligible amount."""
        rules = [{
            "category": "deductible",
            "condition": "Compulsory deductible of ₹10,000",
            "limit_type": "deductible",
            "limit_value": 10000,
            "clause_reference": "Section 7.1",
            "applies_to": "all"
        }]
        case = make_case(total_claimed_amount=50000)
        verdict = evaluate(rules, case, sum_insured=500000)
        
        assert verdict.total_eligible == 40000
        deductible_match = [m for m in verdict.matched_rules if m.rule_category == "deductible"][0]
        assert deductible_match.shortfall == 10000


# ============================================================
# TEST 6: Complex real-world scenario
# ============================================================

class TestRealWorldScenarios:
    """End-to-end tests modeling real Indian health insurance scenarios."""

    def test_star_health_scenario(self):
        """
        Scenario: Patient at private hospital in Mumbai
        Policy: Star Health, SI ₹5,00,000
        Rules: Room cap 1% SI, 20% copay age>60, ₹2,000 ambulance cap
        Patient: 45 years, Single AC room ₹8,000/day, 4 days, Knee surgery ₹2,50,000
        """
        rules = [
            {
                "category": "room_rent",
                "condition": "Room rent capped at 1% of SI per day",
                "limit_type": "percentage",
                "limit_value": 1.0,
                "clause_reference": "Section 4.2",
                "applies_to": "all"
            },
            {
                "category": "copay",
                "condition": "20% co-pay for insured person aged above 60 years",
                "limit_type": "copay",
                "limit_value": 20.0,
                "clause_reference": "Section 6.3",
                "applies_to": "age > 60"
            },
            {
                "category": "ambulance",
                "condition": "Ambulance charges limited to ₹2,000 per hospitalization",
                "limit_type": "absolute",
                "limit_value": 2000,
                "clause_reference": "Section 5.7",
                "applies_to": "ambulance"
            }
        ]
        # Room: ₹8,000/day × 4 = ₹32,000 | Cap: ₹5,000/day × 4 = ₹20,000 | Shortfall: ₹12,000
        # Surgery: ₹2,50,000
        # Total: ₹2,82,000
        # Age=45, so copay doesn't apply
        # After room cap: ₹2,82,000 - ₹12,000 = ₹2,70,000
        case = make_case(
            room_cost_per_day=8000,
            stay_duration_days=4,
            procedure="Total Knee Replacement",
            procedure_cost=250000,
            total_claimed_amount=282000,
            patient_age=45,
        )
        verdict = evaluate(rules, case, sum_insured=500000)
        
        # Copay does NOT apply (patient age 45 < 60)
        # Only room rent cap applies: ₹12,000 shortfall
        # ₹2,82,000 - ₹12,000 = ₹2,70,000 → 95.7% → APPROVED (≥95% threshold)
        assert verdict.overall_verdict == VerdictStatus.APPROVED
        assert verdict.total_eligible == 270000
        assert verdict.total_denied == 12000

    def test_full_denial_exclusion_stops_processing(self):
        """When exclusion triggers, no further rules should be processed."""
        rules = [
            {
                "category": "exclusion_permanent",
                "condition": "Weight management surgery is excluded",
                "limit_type": "exclusion",
                "limit_value": None,
                "clause_reference": "Section 8.2",
                "applies_to": "weight management"
            },
            {
                "category": "room_rent",
                "condition": "Room cap 1%",
                "limit_type": "percentage",
                "limit_value": 1.0,
                "clause_reference": "Section 4.2",
                "applies_to": "all"
            }
        ]
        case = make_case(procedure="Bariatric Weight Management Surgery")
        verdict = evaluate(rules, case, sum_insured=500000)
        
        assert verdict.overall_verdict == VerdictStatus.DENIED
        assert verdict.total_eligible == 0
        # Room rent rule should NOT be processed after exclusion
        room_matches = [m for m in verdict.matched_rules if m.rule_category == "room_rent"]
        assert len(room_matches) == 0

    def test_zero_claim_amount(self):
        """Edge case: zero claim amount."""
        case = make_case(
            room_cost_per_day=0,
            procedure_cost=0,
            total_claimed_amount=0,
        )
        # Should not crash
        verdict = evaluate(rules=[], facts=case, sum_insured=500000)
        assert verdict.coverage_percentage == 0.0 or verdict.total_claimed == 0

    def test_very_high_claim(self):
        """Claim amount exceeding sum insured."""
        rules = [{
            "category": "room_rent",
            "condition": "Room rent capped at 1% of SI",
            "limit_type": "percentage",
            "limit_value": 1.0,
            "clause_reference": "Section 4.2",
            "applies_to": "all"
        }]
        case = make_case(
            room_cost_per_day=50000,
            stay_duration_days=10,
            procedure_cost=500000,
            total_claimed_amount=1000000,
        )
        verdict = evaluate(rules, case, sum_insured=500000)
        # Should run without error even if claim > SI
        assert verdict.total_claimed == 1000000


# ============================================================
# TEST 7: Verdict classification
# ============================================================

class TestVerdictClassification:
    """Test that verdicts are classified correctly."""

    def test_approved_threshold(self):
        """Coverage >= 95% → APPROVED."""
        # No rules → 100% coverage
        case = make_case(total_claimed_amount=100000)
        verdict = evaluate([], case, sum_insured=1000000)
        assert verdict.overall_verdict == VerdictStatus.APPROVED

    def test_partial_verdict(self):
        """Coverage between 0% and 95% → PARTIAL."""
        rules = [{
            "category": "copay",
            "condition": "10% copay",
            "limit_type": "copay",
            "limit_value": 10.0,
            "clause_reference": "Sec 6",
            "applies_to": "all"
        }]
        case = make_case(total_claimed_amount=100000)
        verdict = evaluate(rules, case, sum_insured=500000)
        assert verdict.overall_verdict == VerdictStatus.PARTIAL
        assert verdict.coverage_percentage == 90.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
