"""
Pydantic schemas for verdict / decision output.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class VerdictStatus(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    PARTIAL = "PARTIAL"


class RuleMatchStatus(str, Enum):
    PASSED = "PASSED"       # Claim meets the rule, fully covered
    CAPPED = "CAPPED"       # Claim exceeds limit, partially covered
    DENIED = "DENIED"       # Claim violates rule, not covered
    NOT_APPLICABLE = "N/A"  # Rule doesn't apply to this case


class RuleMatch(BaseModel):
    """Result of applying a single policy rule to the case facts."""
    rule_category: str = Field(..., description="Category of the rule applied")
    rule_condition: str = Field(..., description="The rule condition text")
    status: RuleMatchStatus = Field(..., description="How the case fared against this rule")
    claimed_amount: float = Field(..., description="Amount claimed for this component")
    eligible_amount: float = Field(..., description="Amount eligible after applying this rule")
    shortfall: float = Field(0.0, description="Amount denied/reduced due to this rule")
    clause_reference: str = Field(..., description="Policy clause reference")
    reason: str = Field(..., description="Brief explanation of why this status was assigned")


class Verdict(BaseModel):
    """Complete decision output from the deterministic engine."""
    overall_verdict: VerdictStatus = Field(..., description="Overall claim verdict")
    total_claimed: float = Field(..., description="Total amount claimed")
    total_eligible: float = Field(..., description="Total amount eligible for coverage")
    total_denied: float = Field(0.0, description="Total amount denied")
    coverage_percentage: float = Field(..., description="Percentage of claim covered (0-100)")
    matched_rules: list[RuleMatch] = Field(
        default_factory=list,
        description="Detailed breakdown of each rule application"
    )
    summary: str = Field("", description="Brief one-line summary of the verdict")


class EligibilityResponse(BaseModel):
    """Full eligibility check response returned to the frontend."""
    verdict: Verdict = Field(..., description="The deterministic verdict")
    explanation: str = Field("", description="Patient-friendly explanation from Explanation Agent")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions to improve coverage"
    )
    policy_name: str = Field("", description="Name of the policy checked against")
    insurer: str = Field("", description="Insurance company name")
