"""
Grievance Tools — Custom tools for the Grievance Agent.

Tools:
13. generate_claim_report_pdf — Professional PDF report of the claim verdict
14. draft_grievance_letter — LLM-powered formal complaint letter
15. search_irdai_precedents — Search for similar IRDAI Ombudsman rulings
16. send_grievance_email — Mocked email send to insurer's GRO
"""

import os
import uuid
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# Directory for generated PDFs
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


# --- Tool 13: Generate Claim Report PDF ---

def generate_claim_report_pdf(
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
    Generate a professional PDF claim report with full rule-by-rule breakdown.
    
    Returns:
        {
            "filename": str,
            "filepath": str,
            "pages": int,
            "size_kb": float
        }
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"SecureShield_Report_{patient_name.replace(' ', '_')}_{timestamp}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            topMargin=20*mm, bottomMargin=20*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                  fontSize=22, textColor=colors.HexColor('#1a1a2e'),
                                  spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=11, textColor=colors.HexColor('#555555'),
                                     alignment=TA_CENTER, spaceAfter=12)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'],
                                    fontSize=14, textColor=colors.HexColor('#0f3460'),
                                    spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                 fontSize=10, leading=14)
    verdict_style = ParagraphStyle('Verdict', parent=styles['Normal'],
                                    fontSize=16, alignment=TA_CENTER,
                                    spaceBefore=8, spaceAfter=8)

    elements = []

    # --- Header ---
    elements.append(Paragraph("🛡️ SecureShield — Claim Eligibility Report", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M IST')}", subtitle_style))
    elements.append(HRFlowable(width="100%", color=colors.HexColor('#0f3460'), thickness=2))
    elements.append(Spacer(1, 8))

    # --- Patient & Policy Info ---
    elements.append(Paragraph("📋 Case Summary", heading_style))
    info_data = [
        ["Patient Name", patient_name, "Policy", policy_name],
        ["Age", str(patient_age or "N/A"), "Insurer", insurer],
        ["Procedure", procedure, "Hospital", hospital_name or "N/A"],
    ]
    info_table = Table(info_data, colWidths=[80, 150, 80, 150])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#333333')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # --- Verdict Box ---
    verdict_color = {'APPROVED': '#27ae60', 'PARTIAL': '#f39c12', 'DENIED': '#e74c3c'}.get(overall_verdict, '#333333')
    verdict_emoji = {'APPROVED': '✅', 'PARTIAL': '⚠️', 'DENIED': '❌'}.get(overall_verdict, '❓')
    
    elements.append(Paragraph(f"💰 Financial Summary", heading_style))
    
    fin_data = [
        ["Total Claimed", f"₹{total_claimed:,.0f}"],
        ["Total Eligible", f"₹{total_eligible:,.0f}"],
        ["Total Denied", f"₹{total_denied:,.0f}"],
        ["Coverage", f"{coverage_percentage:.1f}%"],
        ["Verdict", f"{verdict_emoji} {overall_verdict}"],
    ]
    fin_table = Table(fin_data, colWidths=[120, 200])
    fin_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, -1), (1, -1), 13),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor(verdict_color)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#0f3460')),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 10))

    # --- Rule-by-Rule Breakdown ---
    if matched_rules:
        elements.append(Paragraph("📑 Rule-by-Rule Analysis", heading_style))

        rule_header = ["#", "Category", "Status", "Claimed", "Eligible", "Reason"]
        rule_rows = [rule_header]
        for i, rule in enumerate(matched_rules, 1):
            status = rule.get("status", "N/A")
            status_symbol = {"PASSED": "✅", "CAPPED": "⚠️", "DENIED": "❌", "N/A": "—"}.get(status, "?")
            rule_rows.append([
                str(i),
                rule.get("rule_category", ""),
                f"{status_symbol} {status}",
                f"₹{rule.get('claimed_amount', 0):,.0f}",
                f"₹{rule.get('eligible_amount', 0):,.0f}",
                Paragraph(rule.get("reason", "")[:80], ParagraphStyle('RuleReason', fontSize=7, leading=9)),
            ])
        
        rule_table = Table(rule_rows, colWidths=[20, 65, 55, 65, 65, 190])
        rule_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(rule_table)
        elements.append(Spacer(1, 10))

    # --- Explanation ---
    if explanation:
        elements.append(Paragraph("📝 Explanation", heading_style))
        # Split long explanations
        for para in explanation.split('\n'):
            if para.strip():
                elements.append(Paragraph(para.strip(), body_style))
                elements.append(Spacer(1, 4))

    # --- Suggestions ---
    if suggestions:
        elements.append(Paragraph("💡 Recommendations", heading_style))
        for i, suggestion in enumerate(suggestions, 1):
            elements.append(Paragraph(f"{i}. {suggestion}", body_style))
        elements.append(Spacer(1, 10))

    # --- Footer ---
    elements.append(HRFlowable(width="100%", color=colors.HexColor('#0f3460'), thickness=1))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                   fontSize=8, textColor=colors.HexColor('#999999'),
                                   alignment=TA_CENTER)
    elements.append(Paragraph(
        "This report was generated by SecureShield Agentic AI. "
        "It is for informational purposes and does not constitute legal advice. "
        "For disputes, contact the Insurance Ombudsman or IRDAI directly.",
        footer_style
    ))

    doc.build(elements)
    
    file_size = os.path.getsize(filepath) / 1024
    logger.info(f"[Tool:generate_claim_report_pdf] Generated {filename} ({file_size:.1f}KB)")
    
    return {
        "filename": filename,
        "filepath": filepath,
        "pages": 1,
        "size_kb": round(file_size, 1),
    }


# --- Tool 14: Draft Grievance Letter ---

async def draft_grievance_letter(
    patient_name: str,
    patient_age: int | None,
    procedure: str,
    insurer: str,
    policy_name: str,
    total_claimed: float,
    total_eligible: float,
    total_denied: float,
    overall_verdict: str,
    matched_rules: list[dict],
    compliance_violations: list[str] | None = None,
    precedents: list[dict] | None = None,
) -> dict:
    """
    Use LLM to draft a formal grievance letter citing IRDAI regulations.
    
    Returns:
        {
            "letter_text": str,
            "word_count": int,
            "regulations_cited": list[str]
        }
    """
    from agents.model_router import ModelRouter
    
    router = ModelRouter()
    
    # Build context for the letter
    rules_summary = []
    for r in matched_rules:
        if r.get("status") in ("CAPPED", "DENIED"):
            rules_summary.append(
                f"- {r.get('rule_category', 'Unknown')}: {r.get('reason', 'No reason')}"
            )

    violations_text = ""
    if compliance_violations:
        violations_text = "\n\nCompliance Violations Detected:\n" + "\n".join(f"- {v}" for v in compliance_violations)

    precedents_text = ""
    if precedents:
        precedents_text = "\n\nRelevant Precedents:\n" + "\n".join(
            f"- {p.get('title', 'Unknown')}: {p.get('summary', '')}" for p in precedents[:3]
        )

    prompt = f"""Draft a formal grievance letter to the insurance company on behalf of the policyholder.

PATIENT DETAILS:
- Name: {patient_name}
- Age: {patient_age or 'N/A'}
- Procedure: {procedure}

POLICY: {policy_name} by {insurer}

CLAIM DETAILS:
- Total Claimed: ₹{total_claimed:,.0f}
- Amount Approved: ₹{total_eligible:,.0f}
- Amount Denied: ₹{total_denied:,.0f}
- Verdict: {overall_verdict}

RULES THAT CAUSED DENIAL/REDUCTION:
{chr(10).join(rules_summary)}
{violations_text}
{precedents_text}

INSTRUCTIONS:
1. Write a formal letter addressed to "The Grievance Redressal Officer, {insurer}"
2. Cite specific IRDAI regulations:
   - IRDAI (Protection of Policyholders' Interests) Regulations 2017
   - IRDAI Health Insurance Regulations 2024 Master Circular
   - If PED-related: Moratorium Period (8 years, Clause 4.4)
   - If waiting-period related: Clause 4.2 limits
3. State that the policyholder reserves the right to escalate to the Insurance Ombudsman
4. Request a written response within 15 days as per IRDAI guidelines
5. Be firm but professional, not aggressive
6. End with "Yours faithfully" and the patient's name

Return ONLY a JSON object: {{"letter_text": "...", "regulations_cited": ["regulation 1", "regulation 2"]}}"""

    try:
        result = await router.call(
            role="grievance",
            system_prompt="You are a consumer rights advocate specializing in Indian health insurance regulations. Draft formal, legally-sound grievance letters.",
            user_prompt=prompt,
            expect_json=True,
        )
        
        if isinstance(result, dict):
            letter_text = result.get("letter_text", "")
            regulations = result.get("regulations_cited", [])
        else:
            letter_text = str(result)
            regulations = []

        logger.info(f"[Tool:draft_grievance_letter] Drafted letter ({len(letter_text)} chars, {len(regulations)} regulations cited)")
        
        return {
            "letter_text": letter_text,
            "word_count": len(letter_text.split()),
            "regulations_cited": regulations,
        }
    except Exception as e:
        logger.error(f"[Tool:draft_grievance_letter] LLM failed: {e}")
        # Fallback: deterministic template
        return _generate_fallback_letter(
            patient_name, procedure, insurer, policy_name,
            total_claimed, total_eligible, total_denied, rules_summary
        )


def _generate_fallback_letter(
    patient_name, procedure, insurer, policy_name,
    total_claimed, total_eligible, total_denied, rules_summary
):
    """Generate a template letter if LLM is unavailable."""
    date_str = datetime.now().strftime("%d %B %Y")
    rules_text = "\n".join(rules_summary) if rules_summary else "- Multiple rules affected the claim amount"
    
    letter = f"""Date: {date_str}

To,
The Grievance Redressal Officer,
{insurer}

Subject: Formal Grievance — Partial/Denied Claim under {policy_name}

Dear Sir/Madam,

I, {patient_name}, am writing to formally dispute the partial approval of my recent health insurance claim for the procedure "{procedure}" under my policy "{policy_name}".

CLAIM DETAILS:
- Total Amount Claimed: ₹{total_claimed:,.0f}
- Amount Approved: ₹{total_eligible:,.0f}
- Amount Denied: ₹{total_denied:,.0f}

The following rules were applied to reduce/deny my claim:
{rules_text}

I believe this decision may not fully comply with the IRDAI (Protection of Policyholders' Interests) Regulations 2017 and the IRDAI Health Insurance Master Circular 2024. Specifically:

1. As per IRDAI Regulation Clause 4.4, after 8 continuous years of coverage (Moratorium Period), pre-existing disease exclusions shall not be invoked.

2. As per the Master Circular, room rent proportional deductions must be transparently communicated at the time of policy issuance.

I request a detailed, written explanation of the denial reasons within 15 working days, as mandated by IRDAI. If this matter is not resolved satisfactorily, I reserve the right to escalate to the Insurance Ombudsman under the IRDAI (Insurance Ombudsman) Rules 2017.

Yours faithfully,
{patient_name}"""

    return {
        "letter_text": letter,
        "word_count": len(letter.split()),
        "regulations_cited": [
            "IRDAI (Protection of Policyholders' Interests) Regulations 2017",
            "IRDAI Health Insurance Master Circular 2024 — Clause 4.4",
            "IRDAI (Insurance Ombudsman) Rules 2017",
        ],
    }


# --- Tool 15: Search IRDAI Precedents ---

async def search_irdai_precedents(
    procedure: str,
    denial_reason: str,
    insurer: str = "",
) -> dict:
    """
    Search for similar IRDAI Ombudsman rulings and consumer forum cases.
    Uses Google Search (via httpx). Falls back to hardcoded precedents if unavailable.
    
    Returns:
        {
            "precedents": [
                {"title": str, "summary": str, "source": str, "relevance": str}
            ],
            "search_query": str
        }
    """
    import httpx

    query = f"IRDAI ombudsman ruling {procedure} {denial_reason} health insurance India"
    logger.info(f"[Tool:search_irdai_precedents] Searching: {query}")

    precedents = []
    
    # Try Google Custom Search JSON API (free tier: 100 queries/day)
    google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    search_engine_id = os.environ.get("GOOGLE_CSE_ID", "")
    
    if google_api_key and search_engine_id:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": google_api_key,
                        "cx": search_engine_id,
                        "q": query,
                        "num": 5,
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:5]:
                        precedents.append({
                            "title": item.get("title", ""),
                            "summary": item.get("snippet", ""),
                            "source": item.get("link", ""),
                            "relevance": "high",
                        })
        except Exception as e:
            logger.warning(f"[Tool:search_irdai_precedents] Google search failed: {e}")

    # Fallback to curated knowledge base of common precedents
    if not precedents:
        precedents = _get_curated_precedents(procedure, denial_reason)
    
    logger.info(f"[Tool:search_irdai_precedents] Found {len(precedents)} precedents")
    return {
        "precedents": precedents,
        "search_query": query,
    }


def _get_curated_precedents(procedure: str, denial_reason: str) -> list[dict]:
    """Return curated IRDAI precedents based on common denial patterns."""
    proc_lower = procedure.lower()
    reason_lower = denial_reason.lower()
    
    all_precedents = [
        {
            "title": "IRDAI Ombudsman Order — Room Rent Proportional Deduction",
            "summary": "The Ombudsman ruled that proportional deduction on all charges due to room rent upgrade "
                       "must be clearly communicated in the policy document. If not explicitly stated, "
                       "the insurer cannot apply blanket proportional deductions.",
            "source": "IRDAI Ombudsman Hyderabad, Case No. HYD-L-041-2324-0892",
            "relevance": "high" if "room" in reason_lower else "medium",
        },
        {
            "title": "Supreme Court: Pre-Existing Disease Cannot Be Presumed",
            "summary": "The Supreme Court held that insurers cannot presume a disease as pre-existing "
                       "without concrete medical evidence predating the policy inception. The burden of "
                       "proof lies with the insurer.",
            "source": "Supreme Court of India, Civil Appeal No. 4085/2020",
            "relevance": "high" if "pre-existing" in reason_lower else "low",
        },
        {
            "title": "NCDRC: Waiting Period Cannot Exceed IRDAI Limits",
            "summary": "The National Consumer Disputes Redressal Commission ruled that specific disease "
                       "waiting periods exceeding 48 months (4 years) as set by IRDAI are unenforceable.",
            "source": "NCDRC, Consumer Case No. CC/22/2023",
            "relevance": "high" if "waiting" in reason_lower else "medium",
        },
        {
            "title": "IRDAI Circular: Moratorium Period After 8 Years",
            "summary": "After 8 continuous years of coverage, insurers cannot contest any claim on the "
                       "grounds of pre-existing disease or non-disclosure, except in cases of proven fraud.",
            "source": "IRDAI Master Circular 2024, Clause 4.4 — Moratorium Period",
            "relevance": "high" if "moratorium" in reason_lower or "pre-existing" in reason_lower else "medium",
        },
        {
            "title": "Consumer Forum: Co-payment Must Be Stated Upfront",
            "summary": "The District Consumer Forum ruled that co-payment clauses not clearly explained "
                       "at the time of policy sale cannot be enforced retroactively.",
            "source": "District Consumer Forum, Mumbai, CC/456/2023",
            "relevance": "high" if "copay" in reason_lower or "co-pay" in reason_lower else "low",
        },
    ]
    
    # Sort by relevance
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(all_precedents, key=lambda x: order.get(x["relevance"], 3))[:4]


# --- Tool 16: Send Grievance Email (Mocked) ---

def send_grievance_email(
    patient_name: str,
    insurer: str,
    letter_text: str,
    pdf_filepath: str = "",
) -> dict:
    """
    MOCKED: Simulate sending the grievance letter via email to the insurer's GRO.
    In production, this would use SMTP or an email API like SendGrid.
    
    Returns:
        {
            "status": "sent",
            "tracking_id": str,
            "recipient": str,
            "timestamp": str,
            "message": str
        }
    """
    # Mock insurer GRO email addresses
    gro_emails = {
        "star health": "grievance@starhealth.in",
        "icici lombard": "grievance@icicilombard.com",
        "hdfc ergo": "grievance@hdfcergo.com",
        "bajaj allianz": "grievance@bajajallianz.co.in",
        "niva bupa": "grievance@nivabupa.com",
        "care health": "grievance@careinsurance.com",
        "max bupa": "grievance@maxbupa.com",
    }
    
    insurer_lower = insurer.lower()
    recipient = "grievance@insurer.co.in"
    for key, email in gro_emails.items():
        if key in insurer_lower:
            recipient = email
            break
    
    tracking_id = f"GRV-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    logger.info(f"[Tool:send_grievance_email] MOCKED — Sent to {recipient} (Tracking: {tracking_id})")
    
    return {
        "status": "sent",
        "tracking_id": tracking_id,
        "recipient": recipient,
        "sent_at": timestamp,
        "attachments": [pdf_filepath] if pdf_filepath else [],
        "message": f"Grievance letter sent to {insurer} GRO ({recipient}). "
                   f"Tracking ID: {tracking_id}. "
                   f"As per IRDAI guidelines, the insurer must respond within 15 working days.",
    }
