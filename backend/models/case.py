"""
Pydantic schemas for patient case / admission facts.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AdmissionType(str, Enum):
    PLANNED = "planned"
    EMERGENCY = "emergency"


class RoomType(str, Enum):
    GENERAL = "general"
    SEMI_PRIVATE = "semi_private"
    PRIVATE = "private"
    SINGLE_AC = "single_ac"
    DELUXE = "deluxe"
    SUITE = "suite"
    ICU = "icu"


class CityTier(str, Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class CaseFacts(BaseModel):
    """Structured facts extracted from a patient admission case."""
    patient_name: Optional[str] = Field(None, description="Patient name")
    patient_age: Optional[int] = Field(None, description="Patient age in years")
    
    # Admission details
    room_type: RoomType = Field(..., description="Type of room requested")
    room_cost_per_day: float = Field(..., description="Room cost per day in INR")
    stay_duration_days: int = Field(..., description="Expected or actual stay duration in days")
    admission_type: AdmissionType = Field(
        AdmissionType.PLANNED,
        description="Whether admission is planned or emergency"
    )
    
    # Procedure details
    procedure: str = Field(..., description="Name of the medical procedure")
    procedure_cost: Optional[float] = Field(None, description="Procedure/surgery cost in INR")
    
    # Medical history
    pre_existing_conditions: list[str] = Field(
        default_factory=list,
        description="List of pre-existing conditions"
    )
    policy_start_date: Optional[str] = Field(
        None,
        description="Policy start date (for waiting period calculations)"
    )
    policy_tenure_years: int = Field(
        1,
        description="Number of continuous years with the same insurer (for Moratorium Period)"
    )
    is_renewal: bool = Field(
        False, 
        description="Whether this is a renewal policy (transparency requirement)"
    )
    
    # Location
    city_tier: CityTier = Field(
        CityTier.TIER_1,
        description="City tier for location-based limits"
    )
    hospital_name: Optional[str] = Field(None, description="Hospital name")
    
    # Cost breakdown
    total_claimed_amount: float = Field(
        ...,
        description="Total claimed amount in INR (sum of all components)"
    )


class EligibilityCheckRequest(BaseModel):
    """Request to check eligibility for a case against a policy."""
    policy_id: int = Field(..., description="ID of the ingested policy to check against")
    case: CaseFacts = Field(..., description="Patient case details")


class WhatIfRequest(BaseModel):
    """Request for what-if analysis — modify case details and re-check."""
    policy_id: int
    case: CaseFacts
    changed_fields: list[str] = Field(
        default_factory=list,
        description="List of field names the user changed (for highlighting diffs)"
    )
