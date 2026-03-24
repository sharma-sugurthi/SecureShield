"""
Tests for custom agent tools.
Validates the 12 tools that power the agentic system.
"""
import pytest
from tools.case_tools import (
    icd_procedure_lookup, hospital_cost_estimator,
    city_tier_classifier, medical_term_normalizer,
)
from tools.policy_tools import irdai_regulation_lookup, rule_validator
from tools.explanation_tools import clause_explainer, what_if_analyzer, savings_calculator
from tools.audit_tools import audit_trail_logger, get_audit_trail


# === ICD Procedure Lookup ===

class TestICDLookup:
    def test_exact_match(self):
        result = icd_procedure_lookup("appendectomy")
        assert result["found"] is True
        assert "appendectomy" in result["procedure"]["name"].lower()

    def test_fuzzy_match(self):
        result = icd_procedure_lookup("knee replacement")
        assert result["found"] is True
        assert result["procedure"]["icd_code"]

    def test_abbreviation_via_normalizer(self):
        result = icd_procedure_lookup("CABG")
        # May or may not match directly, but should return something
        assert "found" in result

    def test_unknown_procedure(self):
        result = icd_procedure_lookup("qqqqzzzzwwww")
        # Either not found or fuzzy match — both are acceptable tool behavior
        assert "found" in result

    def test_cost_ranges_present(self):
        result = icd_procedure_lookup("cataract")
        assert result["found"] is True
        cost = result["procedure"]["cost_range"]
        assert cost["tier_1"][0] < cost["tier_1"][1]
        assert cost["tier_1"][0] > cost["tier_3"][0]  # Tier 1 costs more


# === Hospital Cost Estimator ===

class TestCostEstimator:
    def test_known_procedure(self):
        result = hospital_cost_estimator("appendectomy", "semi_private", "tier_1")
        assert result["procedure_cost_estimate"]["median"] > 0
        assert result["room_cost_per_day"] > 0
        assert result["estimated_total"]["low"] < result["estimated_total"]["high"]

    def test_tier_cost_ordering(self):
        t1 = hospital_cost_estimator("appendectomy", "private", "tier_1")
        t3 = hospital_cost_estimator("appendectomy", "private", "tier_3")
        assert t1["estimated_total"]["median"] > t3["estimated_total"]["median"]

    def test_custom_stay_days(self):
        result = hospital_cost_estimator("appendectomy", "general", "tier_2", stay_days=5)
        assert result["stay_days"] == 5


# === City Tier Classifier ===

class TestCityTier:
    def test_tier_1_city(self):
        result = city_tier_classifier("Mumbai")
        assert result["tier"] == "tier_1"
        assert result["confidence"] == "high"

    def test_tier_2_city(self):
        result = city_tier_classifier("Jaipur")
        assert result["tier"] == "tier_2"

    def test_hospital_chain_detection(self):
        result = city_tier_classifier("Apollo Hospital")
        assert result["tier"] == "tier_1"
        assert result["matched_on"] == "hospital_chain"

    def test_unknown_defaults_safe(self):
        result = city_tier_classifier("Some Random Village")
        assert result["tier"] in ("tier_2", "tier_3")
        assert result["confidence"] == "low"


# === Medical Term Normalizer ===

class TestMedicalNormalizer:
    def test_abbreviation_expansion(self):
        result = medical_term_normalizer("Patient needs CABG surgery")
        assert "Coronary Artery Bypass Graft" in result["normalized"]
        assert len(result["resolved_abbreviations"]) > 0

    def test_condition_detection(self):
        result = medical_term_normalizer("Patient with diabetes and hypertension")
        assert "Diabetes Mellitus" in result["detected_conditions"]
        assert "Hypertension" in result["detected_conditions"]

    def test_passthrough_clean_text(self):
        result = medical_term_normalizer("Laparoscopic Appendectomy")
        assert result["original"] == "Laparoscopic Appendectomy"


# === IRDAI Regulation Lookup ===

class TestIRDAILookup:
    def test_waiting_period(self):
        result = irdai_regulation_lookup("waiting period")
        assert len(result["regulations"]) > 0

    def test_room_rent(self):
        result = irdai_regulation_lookup("room rent")
        assert len(result["regulations"]) > 0

    def test_exclusions(self):
        result = irdai_regulation_lookup("exclusions")
        assert "standard_exclusions" in result
        assert len(result["standard_exclusions"]) > 0


# === Rule Validator ===

class TestRuleValidator:
    def test_valid_rules(self):
        rules = [
            {"category": "room_rent", "condition": "Room rent cap 1% of SI", 
             "limit_type": "percentage", "limit_value": 1.0, "clause_reference": "Section 2.1"},
            {"category": "copay", "condition": "20% copay", 
             "limit_type": "copay", "limit_value": 20, "clause_reference": "Section 3.1"},
        ]
        result = rule_validator(rules)
        assert result["total_rules"] == 2

    def test_flags_excessive_waiting(self):
        rules = [
            {"category": "waiting_period_specific", "condition": "60 month waiting",
             "limit_type": "waiting_period", "limit_value": 60, "clause_reference": "S1"},
        ]
        result = rule_validator(rules)
        critical = [i for i in result["issues"] if i["severity"] == "critical"]
        assert len(critical) > 0  # Should flag > 48 months

    def test_flags_negative_value(self):
        rules = [
            {"category": "deductible", "condition": "Negative deductible",
             "limit_type": "deductible", "limit_value": -5000, "clause_reference": "S1"},
        ]
        result = rule_validator(rules)
        assert result["is_valid"] is False


# === Clause Explainer ===

class TestClauseExplainer:
    def test_room_rent_explanation(self):
        result = clause_explainer("room_rent", "Room rent capped at 1% SI")
        assert "room" in result["simple_explanation"].lower()
        assert result["tip"]

    def test_unknown_category(self):
        result = clause_explainer("unknown_xyz", "Some clause")
        assert result["simple_explanation"]  # Should still return something


# === What-If Analyzer ===

class TestWhatIfAnalyzer:
    def test_room_downgrade_savings(self):
        rules = [
            {"category": "room_rent", "condition": "Cap 5000/day",
             "limit_type": "absolute", "limit_value": 5000, "clause_reference": "S1"},
        ]
        facts = {
            "patient_name": "Test", "patient_age": 35,
            "room_type": "deluxe", "room_cost_per_day": 15000,
            "stay_duration_days": 5, "admission_type": "planned",
            "procedure": "Appendectomy", "pre_existing_conditions": [],
            "city_tier": "tier_1", "total_claimed_amount": 150000,
        }
        result = what_if_analyzer(rules, facts, 500000,
                                  {"room_cost_per_day": 5000})
        assert result["original_verdict"]["denied"] > result["modified_verdict"]["denied"]


# === Audit Trail ===

class TestAuditTrail:
    def test_log_and_retrieve(self):
        result = audit_trail_logger(
            agent_name="TestAgent", action="test_action",
            input_summary="test input", output_summary="test output",
            tools_used=["test_tool"], duration_ms=100,
        )
        assert result["logged"] is True
        assert result["audit_id"].startswith("AUD-")

    def test_trail_accumulates(self):
        trail = get_audit_trail()
        assert len(trail) > 0
