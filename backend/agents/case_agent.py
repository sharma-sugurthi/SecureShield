"""
Case Analysis Agent — ReAct Tool-Calling Agent
Uses tools to normalize, look up, classify, and validate patient case facts.

Tool Pipeline:
1. medical_term_normalizer → normalize abbreviations, detect conditions
2. icd_procedure_lookup → get ICD codes and cost data
3. city_tier_classifier → classify hospital/city into IRDAI tiers
4. hospital_cost_estimator → validate claimed costs against benchmarks
5. LLM (Gemini Flash) → structure any remaining unstructured fields
"""

import json
import logging
import time
from agents.model_router import router
from models.case import CaseFacts, RoomType, AdmissionType, CityTier
from tools.case_tools import (
    medical_term_normalizer, icd_procedure_lookup,
    city_tier_classifier, hospital_cost_estimator,
)
from tools.vision_tools import google_vision_ocr, is_image
from tools.audit_tools import audit_trail_logger

logger = logging.getLogger(__name__)

# Maps for enum normalization
_ROOM_TYPE_MAP = {
    "general": RoomType.GENERAL, "general ward": RoomType.GENERAL, "ward": RoomType.GENERAL,
    "semi_private": RoomType.SEMI_PRIVATE, "semi private": RoomType.SEMI_PRIVATE,
    "sharing": RoomType.SEMI_PRIVATE, "twin sharing": RoomType.SEMI_PRIVATE,
    "private": RoomType.PRIVATE, "private room": RoomType.PRIVATE,
    "single_ac": RoomType.SINGLE_AC, "single ac": RoomType.SINGLE_AC,
    "single a/c": RoomType.SINGLE_AC, "ac room": RoomType.SINGLE_AC,
    "deluxe": RoomType.DELUXE, "deluxe room": RoomType.DELUXE,
    "suite": RoomType.SUITE, "executive suite": RoomType.SUITE,
    "icu": RoomType.ICU, "intensive care": RoomType.ICU, "critical care": RoomType.ICU,
}

_ADMISSION_MAP = {
    "planned": AdmissionType.PLANNED, "elective": AdmissionType.PLANNED,
    "scheduled": AdmissionType.PLANNED,
    "emergency": AdmissionType.EMERGENCY, "urgent": AdmissionType.EMERGENCY,
    "accident": AdmissionType.EMERGENCY,
}

SYSTEM_PROMPT = """You are an expert hospital billing data analyst.

You have been provided with:
1. NORMALIZED_INPUT: Patient case text after medical term normalization
2. PROCEDURE_DATA: ICD code and cost benchmarks for the procedure
3. CITY_TIER: IRDAI city tier classification for the hospital location
4. COST_BENCHMARK: Expected cost ranges for this procedure in this city tier

YOUR TASK: Structure the raw case input into a complete CaseFacts JSON, using the tool-provided 
data to validate and fill in any missing fields.

IMPORTANT VALIDATION RULES:
- If the claimed amount deviates >50% from the benchmark, flag as "cost_anomaly: true"
- If room cost per day seems unreasonable for the city tier, adjust or flag
- Map all room types to valid enums: general, semi_private, private, single_ac, deluxe, suite, icu
- Map admission type to: planned, emergency
- Map city_tier to: tier_1, tier_2, tier_3

Return ONLY valid JSON matching CaseFacts schema."""


async def extract_case_facts(raw_input: dict) -> CaseFacts:
    """
    Full case analysis pipeline with tool-calling:
    
    Step 1: [Tool] medical_term_normalizer → normalize procedure name and conditions
    Step 2: [Tool] icd_procedure_lookup → get ICD code and cost data
    Step 3: [Tool] city_tier_classifier → classify city/hospital into IRDAI tier
    Step 4: [Tool] hospital_cost_estimator → get cost benchmarks
    Step 5: [LLM] Structure remaining fields (with all tool context)
    
    Each step is audited.
    """
    pipeline_start = time.time()
    logger.info("[CaseAgent] ▶ Starting case analysis pipeline")

    # === Step 0: Handle Image Input (FREE Vision API) ===
    if raw_input.get("file_bytes") and is_image(raw_input.get("filename", "")):
        t0 = time.time()
        ocr_result = google_vision_ocr(raw_input["file_bytes"])
        t1 = time.time()
        
        logger.info(f"[CaseAgent] Image detected. OCR extracted {len(ocr_result['text'])} chars")
        # Treat OCR text as the new raw input for subsequent tools
        raw_input["text_content"] = ocr_result["text"]
        
        audit_trail_logger(
            agent_name="CaseAgent", action="vision_ocr",
            input_summary=f"Image: {raw_input.get('filename')}",
            output_summary=f"Extracted: '{ocr_result['text'][:50]}...'",
            tools_used=["google_vision_ocr"],
            duration_ms=(t1 - t0) * 1000,
        )

    # Pre-extract typed fields (avoid LLM for structured input)
    raw_procedure = str(raw_input.get("procedure", raw_input.get("diagnosis", "")))
    raw_hospital = str(raw_input.get("hospital_name", raw_input.get("hospital", "")))
    raw_city = str(raw_input.get("city", raw_input.get("location", "")))
    raw_room = str(raw_input.get("room_type", "semi_private"))

    # === Step 1: Normalize medical terms ===
    t0 = time.time()
    norm_result = medical_term_normalizer(raw_procedure)
    t1 = time.time()

    normalized_procedure = norm_result.get("detected_procedure") or norm_result["normalized"]
    detected_conditions = norm_result.get("detected_conditions", [])

    audit_trail_logger(
        agent_name="CaseAgent", action="normalize_terms",
        input_summary=f"Raw procedure: '{raw_procedure}'",
        output_summary=f"Normalized: '{normalized_procedure}', conditions: {detected_conditions}",
        tools_used=["medical_term_normalizer"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 2: ICD procedure lookup ===
    t0 = time.time()
    icd_result = icd_procedure_lookup(normalized_procedure)
    t1 = time.time()

    audit_trail_logger(
        agent_name="CaseAgent", action="icd_lookup",
        input_summary=f"Procedure: '{normalized_procedure}'",
        output_summary=f"Found: {icd_result['found']}, ICD: {icd_result['procedure']['icd_code'] if icd_result['found'] and icd_result['procedure'] else 'N/A'}",
        tools_used=["icd_procedure_lookup"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 3: City tier classification ===
    city_input = raw_city or raw_hospital
    t0 = time.time()
    tier_result = city_tier_classifier(city_input) if city_input else {
        "tier": "tier_1", "confidence": "low", "reasoning": "No city/hospital provided, defaulting to Tier 1"
    }
    t1 = time.time()

    audit_trail_logger(
        agent_name="CaseAgent", action="classify_city_tier",
        input_summary=f"Input: '{city_input}'",
        output_summary=f"Tier: {tier_result['tier']}, confidence: {tier_result['confidence']}",
        tools_used=["city_tier_classifier"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 4: Cost estimation ===
    t0 = time.time()
    cost_result = hospital_cost_estimator(
        procedure=normalized_procedure,
        room_type=raw_room,
        city_tier=tier_result["tier"],
        stay_days=raw_input.get("stay_duration_days"),
    )
    t1 = time.time()

    audit_trail_logger(
        agent_name="CaseAgent", action="estimate_costs",
        input_summary=f"Procedure: '{normalized_procedure}', room: {raw_room}, tier: {tier_result['tier']}",
        output_summary=f"Estimated total: ₹{cost_result['estimated_total']['median']:,.0f} "
                       f"(range: ₹{cost_result['estimated_total']['low']:,.0f}-₹{cost_result['estimated_total']['high']:,.0f})",
        tools_used=["hospital_cost_estimator"],
        duration_ms=(t1 - t0) * 1000,
    )

    # === Step 5: Attempt direct structuring first (avoid LLM if input is already structured) ===
    t0 = time.time()
    try:
        facts = _build_facts_from_structured(raw_input, norm_result, icd_result, tier_result, cost_result)
        method = "direct_structuring"
    except Exception as e:
        logger.info(f"[CaseAgent] Direct structuring failed ({e}), using LLM")
        facts = await _build_facts_via_llm(raw_input, norm_result, icd_result, tier_result, cost_result)
        method = "llm_structuring"
    t1 = time.time()

    audit_trail_logger(
        agent_name="CaseAgent", action="structure_facts",
        input_summary=f"Method: {method}",
        output_summary=f"CaseFacts: {facts.procedure}, ₹{facts.total_claimed_amount:,.0f}, "
                       f"{facts.room_type.value}, {facts.city_tier.value}",
        tools_used=[method + (" (model_router)" if method == "llm_structuring" else "")],
        duration_ms=(t1 - t0) * 1000,
    )

    # Cost anomaly check
    claimed = facts.total_claimed_amount
    benchmark_median = cost_result["estimated_total"]["median"]
    if benchmark_median > 0 and abs(claimed - benchmark_median) / benchmark_median > 0.5:
        logger.warning(
            f"[CaseAgent] ⚠ Cost anomaly: claimed ₹{claimed:,.0f} vs benchmark ₹{benchmark_median:,.0f} "
            f"(deviation: {abs(claimed - benchmark_median)/benchmark_median*100:.0f}%)"
        )

    pipeline_end = time.time()
    total_ms = (pipeline_end - pipeline_start) * 1000

    audit_trail_logger(
        agent_name="CaseAgent", action="pipeline_complete",
        input_summary=f"Raw input with {len(raw_input)} fields",
        output_summary=f"CaseFacts ready: {facts.procedure}, ₹{facts.total_claimed_amount:,.0f}",
        tools_used=["medical_term_normalizer", "icd_procedure_lookup", "city_tier_classifier",
                    "hospital_cost_estimator", method],
        duration_ms=total_ms,
    )

    logger.info(f"[CaseAgent] ✓ Pipeline complete in {total_ms:.0f}ms")
    return facts


def _build_facts_from_structured(
    raw: dict, norm: dict, icd: dict, tier: dict, cost: dict
) -> CaseFacts:
    """Build CaseFacts directly from structured input + tool outputs (no LLM needed)."""
    room_key = str(raw.get("room_type", "semi_private")).lower().replace("-", "_").replace(" ", "_")
    room_type = _ROOM_TYPE_MAP.get(room_key, RoomType.SEMI_PRIVATE)

    admission_key = str(raw.get("admission_type", "planned")).lower()
    admission_type = _ADMISSION_MAP.get(admission_key, AdmissionType.PLANNED)

    tier_key = tier.get("tier", "tier_1")
    city_tier = CityTier(tier_key)

    procedure = norm.get("detected_procedure") or str(raw.get("procedure", "Unknown")).strip()
    conditions = list(set(
        raw.get("pre_existing_conditions", []) + norm.get("detected_conditions", [])
    ))

    room_cost = float(raw.get("room_cost_per_day", cost.get("room_cost_per_day", 4000)))
    stay_days = int(raw.get("stay_duration_days", cost.get("stay_days", 3)))
    proc_cost = raw.get("procedure_cost")
    total = float(raw.get("total_claimed_amount", 0))
    if total <= 0:
        total = room_cost * stay_days + (float(proc_cost) if proc_cost else 0)

    return CaseFacts(
        patient_name=raw.get("patient_name"),
        patient_age=raw.get("patient_age"),
        room_type=room_type,
        room_cost_per_day=room_cost,
        stay_duration_days=stay_days,
        admission_type=admission_type,
        procedure=procedure,
        procedure_cost=proc_cost,
        pre_existing_conditions=conditions,
        policy_start_date=raw.get("policy_start_date"),
        city_tier=city_tier,
        hospital_name=raw.get("hospital_name"),
        total_claimed_amount=total,
    )


async def _build_facts_via_llm(
    raw: dict, norm: dict, icd: dict, tier: dict, cost: dict
) -> CaseFacts:
    """Fallback: use LLM to structure ambiguous or text-heavy input."""
    user_prompt = f"""Structure the following patient case data into a valid CaseFacts JSON.

RAW INPUT: {json.dumps(raw, indent=2, default=str)}

TOOL-PROVIDED CONTEXT:
- Normalized Procedure: {norm.get('detected_procedure', norm['normalized'])}
- Detected Conditions: {norm.get('detected_conditions', [])}
- ICD Procedure Match: {json.dumps(icd.get('procedure', {}), default=str)[:500]}
- City Tier: {tier.get('tier', 'tier_1')} (confidence: {tier.get('confidence', 'low')})
- Cost Benchmark (median): ₹{cost['estimated_total']['median']:,.0f}
- Room Cost/Day Benchmark: ₹{cost.get('room_cost_per_day', 'N/A')}

Required fields: room_type (enum), room_cost_per_day, stay_duration_days, admission_type (enum),
procedure, city_tier (enum), total_claimed_amount.

Return ONLY valid JSON."""

    result = await router.call_json(
        role="case_analysis",
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.05,
    )

    return CaseFacts(**result)
