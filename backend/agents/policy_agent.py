"""
Policy Ingestion Agent — ReAct Tool-Calling Agent
Uses tools to extract, analyze, validate, and store policy rules.

Tool Pipeline:
1. pdf_text_extractor → raw text
2. pdf_table_extractor → structured tables
3. irdai_regulation_lookup → cross-reference
4. rule_validator → quality check
5. LLM (Gemini Flash) → structured rule extraction from text + tables
"""

import hashlib
import json
import logging
import time
from agents.model_router import router
from models.policy import PolicyDocument, PolicyRule, LimitType
from db.database import save_policy
from security import validate_pdf_upload
from tools.policy_tools import (
    pdf_text_extractor, pdf_table_extractor,
    irdai_regulation_lookup, rule_validator,
)
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Indian health insurance policy analyst with deep IRDAI knowledge.

You have already been provided with:
1. TEXT: Full text extracted from the PDF (by pdf_text_extractor tool)
2. TABLES: Structured tables found in the PDF (by pdf_table_extractor tool)
3. IRDAI_CONTEXT: Relevant IRDAI regulations (by irdai_regulation_lookup tool)

YOUR TASK: Using ALL of this information, extract EVERY rule, limit, cap, sub-limit, 
exclusion, waiting period, co-payment, deductible, and condition.

CATEGORIES: room_rent, icu, copay, sublimit, exclusion_permanent, exclusion_temporary,
waiting_period_initial, waiting_period_specific, waiting_period_pec, deductible,
ambulance, daycare, pre_post_hospitalization, restoration, no_claim_bonus,
network_hospital, domiciliary, maternity, other

Each rule MUST have: category, condition, limit_type, limit_value (or null), 
clause_reference, applies_to.

LIMIT TYPES: percentage | absolute | sublimit | exclusion | copay | waiting_period | deductible

IMPORTANT: Cross-reference extracted rules against the IRDAI regulations provided.
Flag if any rule violates IRDAI mandated limits (e.g., waiting period > 48 months).

Return ONLY a JSON object: {"insurer": "", "plan_name": "", "sum_insured": 0, 
"policy_type": "", "rules": [...]}"""


def _validate_and_clean_rules(raw_rules: list[dict]) -> list[PolicyRule]:
    """Validate extracted rules, fix common LLM output issues, and return clean PolicyRule list."""
    valid_categories = {
        "room_rent", "icu", "copay", "sublimit", "exclusion_permanent", "exclusion_temporary",
        "waiting_period_initial", "waiting_period_specific", "waiting_period_pec", "deductible",
        "ambulance", "daycare", "pre_post_hospitalization", "restoration", "no_claim_bonus",
        "network_hospital", "domiciliary", "maternity", "other"
    }

    limit_type_map = {
        "percentage": "percentage", "percent": "percentage",
        "absolute": "absolute", "fixed": "absolute",
        "sublimit": "sublimit", "sub_limit": "sublimit",
        "exclusion": "exclusion", "excluded": "exclusion",
        "copay": "copay", "co_pay": "copay", "co-pay": "copay",
        "waiting_period": "waiting_period", "waiting": "waiting_period",
        "deductible": "deductible",
    }

    validated = []
    seen_conditions = set()

    for raw in raw_rules:
        try:
            cat = raw.get("category", "other").lower().strip().replace("-", "_").replace(" ", "_")
            if cat not in valid_categories:
                if "room" in cat: cat = "room_rent"
                elif "exclu" in cat: cat = "exclusion_permanent"
                elif "wait" in cat: cat = "waiting_period_specific"
                elif "copay" in cat: cat = "copay"
                else: cat = "other"
            raw["category"] = cat

            lt = raw.get("limit_type", "absolute").lower().strip().replace("-", "_")
            raw["limit_type"] = limit_type_map.get(lt, "absolute")

            if not raw.get("clause_reference"):
                raw["clause_reference"] = "Not specified"
            if not raw.get("condition"):
                continue

            cond_key = raw["condition"].lower().strip()[:100]
            if cond_key in seen_conditions:
                continue
            seen_conditions.add(cond_key)

            # Clean limit_value: extract number from strings like "24 months", "₹5,000", "30 days"
            lv = raw.get("limit_value")
            if isinstance(lv, str) and lv.strip():
                import re
                nums = re.findall(r'[\d,.]+', lv.replace(',', ''))
                if nums:
                    try:
                        raw["limit_value"] = float(nums[0])
                    except (ValueError, IndexError):
                        raw["limit_value"] = None
                else:
                    raw["limit_value"] = None

            rule = PolicyRule(**raw)
            validated.append(rule)
        except Exception as e:
            logger.warning(f"[PolicyAgent] Skipping invalid rule: {e}")

    return validated


async def ingest_policy(pdf_bytes: bytes, filename: str = "policy.pdf") -> PolicyDocument:
    """
    Full policy ingestion pipeline with tool-calling ReAct pattern:
    
    Step 1: [Tool] pdf_text_extractor → extract raw text
    Step 2: [Tool] pdf_table_extractor → extract structured tables
    Step 3: [Tool] irdai_regulation_lookup → get relevant regulations
    Step 4: [LLM] Gemini Flash → structured rule extraction (with all tool outputs as context)
    Step 5: [Tool] rule_validator → validate extracted rules
    Step 6: [DB] save_policy → persist to database
    
    Each step is audited for compliance traceability.
    """
    pipeline_start = time.time()
    logger.info(f"[PolicyAgent] ▶ Starting ingestion pipeline for {filename}")

    # --- Security validation ---
    validate_pdf_upload(pdf_bytes, filename)

    # === Step 1: Extract text (Tool: pdf_text_extractor) ===
    t0 = time.time()
    text_result = pdf_text_extractor(pdf_bytes)
    t1 = time.time()

    if text_result["total_chars"] < 100:
        raise ValueError("Could not extract meaningful text. The PDF may be scanned/image-based.")

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="extract_text",
        input_summary=f"PDF: {filename} ({len(pdf_bytes)/1024:.0f}KB)",
        output_summary=f"Extracted {text_result['total_chars']} chars from {text_result['total_pages']} pages",
        tools_used=["pdf_text_extractor"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 2: Extract tables (Tool: pdf_table_extractor) ===
    t0 = time.time()
    table_result = pdf_table_extractor(pdf_bytes)
    t1 = time.time()

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="extract_tables",
        input_summary=f"PDF: {filename}",
        output_summary=f"Found {table_result['tables_found']} tables: {[t['type'] for t in table_result['tables']]}",
        tools_used=["pdf_table_extractor"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 3: IRDAI regulation lookup (Tool: irdai_regulation_lookup) ===
    t0 = time.time()
    irdai_context = irdai_regulation_lookup("health insurance comprehensive")
    irdai_room = irdai_regulation_lookup("room rent")
    irdai_copay = irdai_regulation_lookup("co-payment")
    irdai_exclusions = irdai_regulation_lookup("exclusions")
    t1 = time.time()

    # Merge IRDAI results
    irdai_combined = {
        "definitions": irdai_context["definitions"],
        "regulations": irdai_context["regulations"] + irdai_room["regulations"] + irdai_copay["regulations"],
        "standard_exclusions": irdai_exclusions.get("standard_exclusions", {}),
    }

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="irdai_cross_reference",
        input_summary="Looked up: comprehensive, room rent, co-payment, exclusions",
        output_summary=f"Found {len(irdai_combined['definitions'])} definitions, "
                       f"{len(irdai_combined['regulations'])} regulations",
        tools_used=["irdai_regulation_lookup"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 4: LLM-based rule extraction (with ALL tool outputs as context) ===
    # Combine all text
    full_text = "\n\n".join(p["text"] for p in text_result["pages"] if p["text"])
    text_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]

    # Format table data for LLM
    table_context = ""
    if table_result["tables"]:
        table_context = "\n\nSTRUCTURED TABLES FOUND IN DOCUMENT:\n"
        for t in table_result["tables"]:
            table_context += f"\n[Table Type: {t['type']}, Page {t['page']}, {t['row_count']} rows]\n"
            if t.get("header"):
                table_context += f"Header: {t['header']}\n"
            for row in t.get("rows", [])[:10]:  # Limit rows
                table_context += f"  {row}\n"

    # Format IRDAI context for LLM
    irdai_text = f"\n\nIRDAI REGULATIONS FOR CROSS-REFERENCE:\n{json.dumps(irdai_combined, indent=2, default=str)[:3000]}"

    user_prompt = f"""Analyze and extract ALL insurance rules from this policy document.

EXTRACTED TEXT ({text_result['total_chars']} characters, {text_result['total_pages']} pages):
{full_text[:15000]}
{table_context}
{irdai_text}

INSTRUCTIONS:
- Extract EVERY rule from both the text AND the tables.
- Cross-reference against IRDAI regulations — flag any violations.
- Include exact clause/section references.
- Return ONLY valid JSON."""

    t0 = time.time()
    result = await router.call_json(
        role="policy_ingestion",
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.05,
        max_tokens=8192,
    )
    t1 = time.time()

    insurer = result.get("insurer", "Unknown Insurer")
    plan_name = result.get("plan_name", "Unknown Plan")
    sum_insured = float(result.get("sum_insured", 0))
    policy_type = result.get("policy_type", "individual")
    raw_rules = result.get("rules", [])

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="llm_rule_extraction",
        input_summary=f"Sent {len(user_prompt)} chars to LLM with text + tables + IRDAI context",
        output_summary=f"LLM extracted {len(raw_rules)} raw rules from {insurer} — {plan_name}",
        tools_used=["model_router.call_json(policy_ingestion)"],
        duration_ms=(t1 - t0) * 1000,
        metadata={"model_role": "policy_ingestion", "raw_rule_count": len(raw_rules)},
    )

    if not raw_rules:
        raise ValueError("No rules extracted. Please ensure the PDF is a valid health insurance policy.")

    # === Step 5: Validate rules (Tool: rule_validator) ===
    t0 = time.time()
    validated_rules = _validate_and_clean_rules(raw_rules)
    validation_report = rule_validator([r.model_dump() for r in validated_rules], sum_insured)
    t1 = time.time()

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="validate_rules",
        input_summary=f"{len(raw_rules)} raw rules → {len(validated_rules)} valid rules",
        output_summary=f"Validation: {len(validation_report['issues'])} issues, "
                       f"missing categories: {validation_report['categories_missing']}",
        tools_used=["rule_validator"],
        duration_ms=(t1 - t0) * 1000,
        metadata={"validation_report": validation_report},
    )

    # Log critical issues
    for issue in validation_report["issues"]:
        if issue["severity"] == "critical":
            logger.warning(f"[PolicyAgent] CRITICAL: {issue['message']}")

    # === Step 6: Save to database ===
    policy_id = await save_policy(
        insurer=insurer,
        plan_name=plan_name,
        sum_insured=sum_insured,
        policy_type=policy_type,
        rules=[r.model_dump() for r in validated_rules],
        raw_text_hash=text_hash,
    )

    pipeline_end = time.time()
    total_ms = (pipeline_end - pipeline_start) * 1000

    audit_trail_logger(
        agent_name="PolicyAgent",
        action="pipeline_complete",
        input_summary=f"PDF: {filename}",
        output_summary=f"Policy #{policy_id}: {insurer} — {plan_name}, SI: ₹{sum_insured:,.0f}, "
                       f"{len(validated_rules)} rules",
        tools_used=["pdf_text_extractor", "pdf_table_extractor", "irdai_regulation_lookup",
                    "model_router", "rule_validator", "save_policy"],
        duration_ms=total_ms,
        metadata={
            "policy_id": policy_id,
            "tables_found": table_result["tables_found"],
            "validation_issues": len(validation_report["issues"]),
        },
    )

    logger.info(f"[PolicyAgent] ✓ Pipeline complete in {total_ms:.0f}ms — "
                f"Policy #{policy_id}: {len(validated_rules)} rules")

    return PolicyDocument(
        id=policy_id,
        insurer=insurer,
        plan_name=plan_name,
        sum_insured=sum_insured,
        policy_type=policy_type,
        rules=validated_rules,
        raw_text_hash=text_hash,
    )
