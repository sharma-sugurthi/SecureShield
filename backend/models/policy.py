"""
Pydantic schemas for insurance policy rules.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class LimitType(str, Enum):
    PERCENTAGE = "percentage"
    ABSOLUTE = "absolute"
    SUBLIMIT = "sublimit"
    EXCLUSION = "exclusion"
    COPAY = "copay"
    WAITING_PERIOD = "waiting_period"
    DEDUCTIBLE = "deductible"


class PolicyRule(BaseModel):
    """A single extracted rule from a policy document."""
    category: str = Field(
        ...,
        description="Rule category: room_rent, copay, sublimit, exclusion, waiting_period, deductible, etc."
    )
    condition: str = Field(
        ...,
        description="Human-readable condition text, e.g. 'Room rent capped at 1% of sum insured per day'"
    )
    limit_type: LimitType = Field(
        ...,
        description="Type of limit applied by this rule"
    )
    limit_value: Optional[float] = Field(
        None,
        description="Numeric limit value (percentage as decimal, absolute in INR)"
    )
    limit_unit: Optional[str] = Field(
        None,
        description="Unit for the limit: 'per_day', 'per_claim', 'per_year', 'per_illness', etc."
    )
    clause_reference: str = Field(
        ...,
        description="Reference to the specific clause in the policy document"
    )
    applies_to: Optional[str] = Field(
        None,
        description="What this rule applies to: 'all', specific procedure types, room types, etc."
    )


class PolicyDocument(BaseModel):
    """Structured representation of an insurance policy."""
    id: Optional[int] = None
    insurer: str = Field(..., description="Insurance company name")
    plan_name: str = Field(..., description="Policy plan name")
    sum_insured: float = Field(..., description="Sum insured amount in INR")
    policy_type: str = Field(
        "individual",
        description="Policy type: individual, family_floater, group"
    )
    rules: list[PolicyRule] = Field(
        default_factory=list,
        description="List of extracted policy rules"
    )
    raw_text_hash: Optional[str] = Field(
        None,
        description="Hash of the raw PDF text for deduplication"
    )
    is_reviewed: bool = Field(
        False,
        description="Whether the extracted rules have been human-reviewed"
    )


class PolicyUploadResponse(BaseModel):
    """Response after uploading and processing a policy PDF."""
    policy_id: int
    insurer: str
    plan_name: str
    sum_insured: float
    rules_count: int
    message: str
