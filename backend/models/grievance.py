"""
Pydantic schemas for the Grievance Agent pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional


class GrievanceRequest(BaseModel):
    """Request to generate a grievance package for a denied/partial claim."""
    policy_id: int = Field(..., description="Policy ID used in the eligibility check")
    check_id: Optional[int] = Field(None, description="ID of the eligibility check to dispute")
    # Re-pass the verdict data directly for simplicity
    verdict_summary: str = Field("", description="One-line verdict summary")
    overall_verdict: str = Field("PARTIAL", description="APPROVED / PARTIAL / DENIED")
    total_claimed: float = Field(0, description="Total amount claimed")
    total_eligible: float = Field(0, description="Total amount eligible")
    total_denied: float = Field(0, description="Total amount denied")
    coverage_percentage: float = Field(0, description="Coverage percentage")
    patient_name: str = Field("Patient", description="Patient name")
    patient_age: Optional[int] = Field(None, description="Patient age")
    procedure: str = Field("", description="Procedure name")
    hospital_name: str = Field("", description="Hospital name")
    insurer: str = Field("", description="Insurance company name")
    policy_name: str = Field("", description="Policy plan name")
    matched_rules: list[dict] = Field(default_factory=list, description="Rule-by-rule breakdown")
    explanation: str = Field("", description="Explanation text from Explanation Agent")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions from Explanation Agent")


class GrievanceResponse(BaseModel):
    """Response from the Grievance Agent pipeline."""
    status: str = Field("success", description="Pipeline status")
    pdf_filename: str = Field("", description="Filename of the generated PDF report")
    pdf_download_url: str = Field("", description="URL to download the PDF")
    grievance_letter: str = Field("", description="Full text of the drafted grievance letter")
    precedents: list[dict] = Field(default_factory=list, description="IRDAI precedent search results")
    email_status: dict = Field(default_factory=dict, description="Mocked email send confirmation")
    tools_used: list[str] = Field(default_factory=list, description="Tools invoked during pipeline")
    compliance_violations: list[str] = Field(default_factory=list, description="Detected compliance violations")
