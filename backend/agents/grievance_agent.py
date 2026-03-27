"""
Grievance Agent — ReAct Tool-Calling Agent

Orchestrates the grievance pipeline when a claim is denied or partially approved.

Tool Pipeline:
1. search_irdai_precedents → find similar rulings
2. draft_grievance_letter → LLM-powered formal letter
3. generate_claim_report_pdf → professional PDF report
4. send_grievance_email → mock email to insurer GRO

The agent first analyzes the verdict for compliance violations, then
autonomously decides which tools to invoke based on the situation.
"""

import logging
from tools.grievance_tools import (
    generate_claim_report_pdf,
    draft_grievance_letter,
    search_irdai_precedents,
    send_grievance_email,
)
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)


async def run_grievance_pipeline(
    patient_name: str,
    patient_age: int | None,
    procedure: str,
    hospital_name: str,
    insurer: str,
    policy_name: str,
    total_claimed: float,
    total_eligible: float,
    total_denied: float,
    coverage_percentage: float,
    overall_verdict: str,
    matched_rules: list[dict],
    explanation: str = "",
    suggestions: list[str] | None = None,
) -> dict:
    """
    Full grievance pipeline with tool-calling:

    Step 1: Detect compliance violations from matched rules
    Step 2: [Tool] search_irdai_precedents → find similar rulings
    Step 3: [Tool] draft_grievance_letter → formal complaint letter
    Step 4: [Tool] generate_claim_report_pdf → professional report
    Step 5: [Tool] send_grievance_email → mock send to insurer
    """
    logger.info(f"[GrievanceAgent] Starting pipeline for {patient_name} — {overall_verdict}")
    tools_used = []
    compliance_violations = []

    # --- Step 1: Detect Compliance Violations ---
    audit_trail_logger("grievance_agent", "compliance_check",
                       {"action": "Analyzing verdict for compliance violations"})

    for rule in matched_rules:
        status = rule.get("status", "")
        reason = (rule.get("reason", "") or "").lower()
        category = (rule.get("rule_category", "") or "").lower()

        # Check for Moratorium Period violation
        if "pre-existing" in reason or "ped" in reason:
            compliance_violations.append(
                "Potential Moratorium Period violation: "
                "If policy has been active for 8+ continuous years, "
                "PED exclusions cannot be invoked (IRDAI Master Circular 2024, Clause 4.4)."
            )
        
        # Check for disproportionate room rent deduction
        if category == "room_rent" and status == "CAPPED":
            shortfall = rule.get("shortfall", 0)
            if shortfall > 0:
                compliance_violations.append(
                    f"Room rent proportional deduction of ₹{shortfall:,.0f} applied. "
                    "Verify that proportional deductions were clearly communicated "
                    "in the policy schedule (IRDAI PPHI 2017, Section 7)."
                )

        # Check for excessive copay
        if category == "copay" and status == "CAPPED":
            compliance_violations.append(
                "Co-payment clause applied. Verify that the co-pay percentage was "
                "clearly disclosed at the time of policy sale (Consumer Protection Act 2019, Section 2(46))."
            )

    # De-duplicate
    compliance_violations = list(set(compliance_violations))
    
    logger.info(f"[GrievanceAgent] Found {len(compliance_violations)} potential compliance issues")
    audit_trail_logger("grievance_agent", "compliance_result",
                       {"violations_found": len(compliance_violations), "violations": compliance_violations})

    # --- Step 2: Search IRDAI Precedents ---
    audit_trail_logger("grievance_agent", "tool_call",
                       {"tool": "search_irdai_precedents", "action": "Searching for similar IRDAI rulings"})
    
    primary_denial_reason = ""
    for rule in matched_rules:
        if rule.get("status") in ("CAPPED", "DENIED"):
            primary_denial_reason = rule.get("reason", "claim denied")
            break

    precedent_result = await search_irdai_precedents(
        procedure=procedure,
        denial_reason=primary_denial_reason,
        insurer=insurer,
    )
    tools_used.append("search_irdai_precedents")
    
    audit_trail_logger("grievance_agent", "tool_result",
                       {"tool": "search_irdai_precedents",
                        "precedents_found": len(precedent_result.get("precedents", []))})

    # --- Step 3: Draft Grievance Letter ---
    audit_trail_logger("grievance_agent", "tool_call",
                       {"tool": "draft_grievance_letter", "action": "Drafting formal complaint letter using LLM"})
    
    letter_result = await draft_grievance_letter(
        patient_name=patient_name,
        patient_age=patient_age,
        procedure=procedure,
        insurer=insurer,
        policy_name=policy_name,
        total_claimed=total_claimed,
        total_eligible=total_eligible,
        total_denied=total_denied,
        overall_verdict=overall_verdict,
        matched_rules=matched_rules,
        compliance_violations=compliance_violations,
        precedents=precedent_result.get("precedents", []),
    )
    tools_used.append("draft_grievance_letter")
    
    audit_trail_logger("grievance_agent", "tool_result",
                       {"tool": "draft_grievance_letter",
                        "word_count": letter_result.get("word_count", 0),
                        "regulations_cited": letter_result.get("regulations_cited", [])})

    # --- Step 4: Generate PDF Report ---
    audit_trail_logger("grievance_agent", "tool_call",
                       {"tool": "generate_claim_report_pdf", "action": "Generating professional PDF report"})
    
    pdf_result = generate_claim_report_pdf(
        patient_name=patient_name,
        patient_age=patient_age,
        procedure=procedure,
        hospital_name=hospital_name,
        insurer=insurer,
        policy_name=policy_name,
        total_claimed=total_claimed,
        total_eligible=total_eligible,
        total_denied=total_denied,
        coverage_percentage=coverage_percentage,
        overall_verdict=overall_verdict,
        matched_rules=matched_rules,
        explanation=explanation,
        suggestions=suggestions,
    )
    tools_used.append("generate_claim_report_pdf")
    
    audit_trail_logger("grievance_agent", "tool_result",
                       {"tool": "generate_claim_report_pdf",
                        "filename": pdf_result.get("filename", ""),
                        "size_kb": pdf_result.get("size_kb", 0)})

    # --- Step 5: Send Grievance Email (Mocked) ---
    audit_trail_logger("grievance_agent", "tool_call",
                       {"tool": "send_grievance_email", "action": "Sending grievance to insurer GRO"})
    
    email_result = send_grievance_email(
        patient_name=patient_name,
        insurer=insurer,
        letter_text=letter_result.get("letter_text", ""),
        pdf_filepath=pdf_result.get("filepath", ""),
    )
    tools_used.append("send_grievance_email")
    
    audit_trail_logger("grievance_agent", "tool_result",
                       {"tool": "send_grievance_email",
                        "status": email_result.get("status", ""),
                        "tracking_id": email_result.get("tracking_id", "")})

    logger.info(f"[GrievanceAgent] Pipeline complete — {len(tools_used)} tools invoked")
    audit_trail_logger("grievance_agent", "pipeline_complete",
                       {"tools_used": tools_used, "total_tools": len(tools_used)})

    return {
        "status": "success",
        "pdf_filename": pdf_result.get("filename", ""),
        "pdf_download_url": f"/api/download-report/{pdf_result.get('filename', '')}",
        "grievance_letter": letter_result.get("letter_text", ""),
        "precedents": precedent_result.get("precedents", []),
        "email_status": email_result,
        "tools_used": tools_used,
        "compliance_violations": compliance_violations,
    }
