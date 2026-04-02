"""
Policy Ingestion Tools — Custom tools for the Policy Agent.

Tools:
1. pdf_text_extractor — Extract text from PDF pages
2. pdf_table_extractor — Extract tables from PDF (sub-limits, exclusion lists)
3. irdai_regulation_lookup — Cross-reference against IRDAI mandated rules
4. rule_validator — Validate extracted rules for completeness and accuracy
"""

import json
import logging
import os
import fitz  # PyMuPDF
from pathlib import Path

logger = logging.getLogger(__name__)

# Load knowledge base
_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
with open(_KNOWLEDGE_DIR / "irdai_rules.json", "r") as f:
    IRDAI_KB = json.load(f)


# --- Tool 1: PDF Text Extractor ---

def pdf_text_extractor(pdf_bytes: bytes) -> dict:
    """
    Extract text from a PDF document, page-by-page.
    
    Returns:
        {
            "total_pages": int,
            "total_chars": int,
            "pages": [{"page_num": 1, "text": "...", "char_count": int}]
        }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    total_chars = 0

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        char_count = len(text.strip())
        total_chars += char_count
        pages.append({
            "page_num": page_num + 1,
            "text": text.strip(),
            "char_count": char_count,
        })

    doc.close()

    logger.info(f"[Tool:pdf_text_extractor] Extracted {total_chars} chars from {len(pages)} pages")
    return {
        "total_pages": len(pages),
        "total_chars": total_chars,
        "pages": pages,
    }


# --- Tool 2: PDF Table Extractor ---

def pdf_table_extractor(pdf_bytes: bytes) -> dict:
    """
    Extract structured tables from a PDF, targeting common insurance policy table formats:
    - Sub-limit tables (procedure name → max amount)
    - Exclusion lists (numbered or bulleted)
    - Waiting period tables
    - Room rent schedule
    
    Returns:
        {
            "tables_found": int,
            "tables": [{"page": int, "type": str, "rows": list[list[str]]}]
        }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    tables = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)

        # PyMuPDF table extraction (v1.23+)
        try:
            page_tables = page.find_tables()
            for tab in page_tables:
                table_data = tab.extract()
                if table_data and len(table_data) > 1:  # At least header + 1 row
                    # Classify table type
                    header_text = " ".join(str(cell) for cell in table_data[0] if cell).lower()
                    table_type = _classify_table(header_text)

                    tables.append({
                        "page": page_num + 1,
                        "type": table_type,
                        "header": table_data[0],
                        "rows": table_data[1:],
                        "row_count": len(table_data) - 1,
                    })
        except AttributeError:
            # Older PyMuPDF without find_tables — fallback to text-based detection
            text = page.get_text("text")
            detected = _extract_tables_from_text(text, page_num + 1)
            tables.extend(detected)

    doc.close()

    logger.info(f"[Tool:pdf_table_extractor] Found {len(tables)} tables")
    return {
        "tables_found": len(tables),
        "tables": tables,
    }


def _classify_table(header_text: str) -> str:
    """Classify an insurance policy table by its header."""
    header_lower = header_text.lower()
    if any(w in header_lower for w in ["sub-limit", "sublimit", "maximum", "cap", "limit"]):
        return "sublimit_schedule"
    elif any(w in header_lower for w in ["exclusion", "excluded", "not covered"]):
        return "exclusion_list"
    elif any(w in header_lower for w in ["waiting", "period"]):
        return "waiting_period_schedule"
    elif any(w in header_lower for w in ["room", "rent", "accommodation"]):
        return "room_rent_schedule"
    elif any(w in header_lower for w in ["co-pay", "copay", "co pay"]):
        return "copay_schedule"
    elif any(w in header_lower for w in ["benefit", "coverage", "feature"]):
        return "benefit_summary"
    return "other"


def _extract_tables_from_text(text: str, page_num: int) -> list[dict]:
    """Fallback: extract table-like structures from plain text."""
    tables = []
    lines = text.strip().split("\n")
    
    # Look for lines with multiple tab/space-separated columns
    table_lines = []
    for line in lines:
        parts = [p.strip() for p in line.split("  ") if p.strip()]  # Double-space separated
        if len(parts) >= 2:
            table_lines.append(parts)
        elif table_lines and len(table_lines) >= 3:
            # End of a table-like section
            header_text = " ".join(table_lines[0]).lower()
            tables.append({
                "page": page_num,
                "type": _classify_table(header_text),
                "header": table_lines[0],
                "rows": table_lines[1:],
                "row_count": len(table_lines) - 1,
            })
            table_lines = []

    # Handle remaining lines
    if len(table_lines) >= 3:
        header_text = " ".join(table_lines[0]).lower()
        tables.append({
            "page": page_num,
            "type": _classify_table(header_text),
            "header": table_lines[0],
            "rows": table_lines[1:],
            "row_count": len(table_lines) - 1,
        })

    return tables


# --- Tool 5: Rule-Based Policy Extractor ---

def rule_based_policy_extractor(text: str) -> dict:
    """
    Extract basic policy info using regex/rules (FREE, No API).
    Targets: Insurer Name, Plan Name, Sum Insured.
    """
    import re
    result = {
        "insurer": None,
        "plan_name": None,
        "sum_insured": None,
        "confidence": 0.0
    }
    
    # Common Insurer patterns
    insurers = [
        "Star Health", "HDFC ERGO", "ICICI Lombard", "Niva Bupa", "Care Health",
        "Aditya Birla", "TATA AIG", "Bajaj Allianz", "SBI General", "Oriental Insurance",
        "United India", "New India Assurance", "National Insurance"
    ]
    for insurer in insurers:
        if insurer.lower() in text.lower():
            result["insurer"] = insurer
            result["confidence"] += 0.3
            break
            
    # Sum Insured patterns (e.g. "Sum Insured: 5,00,000", "SI - 10 Lakhs")
    si_patterns = [
        r"(?:Sum Insured|S\.I\.|Total SI)\s*[:\-\s]*[₹Rs\.]*\s*([\d,]+)",
        r"([\d,]+)\s*(?:Lakhs|Lakh|L)",
    ]
    for pattern in si_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(",", "")
            try:
                # Handle "10 Lakhs" vs "1000000"
                if "Lakh" in pattern or (match.group(0).lower().find("lakh") != -1):
                    result["sum_insured"] = float(val) * 100000
                else:
                    result["sum_insured"] = float(val)
                result["confidence"] += 0.4
                break
            except: continue
            
    # Plan Name patterns
    plan_patterns = [
        r"(?:Plan|Product|Policy)\s*Name\s*[:\-\s]*([A-Z][a-zA-Z0-aligned\s]{3,30})",
        r"(?:Plan|Product)\s*[:\-\s]*([A-Z][a-zA-Z\s]{3,30})",
    ]
    for pattern in plan_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if len(name) > 5:
                result["plan_name"] = name
                result["confidence"] += 0.2
                break
                
    return result


# --- Tool 3: IRDAI Regulation Lookup ---

def irdai_regulation_lookup(query: str) -> dict:
    """
    Look up IRDAI regulations, standard definitions, and mandated limits.
    
    Args:
        query: Topic to look up (e.g., "waiting period", "room rent", "co-payment", "exclusion")
    
    Returns:
        {
            "query": str,
            "definitions": [matching standard definitions],
            "regulations": [matching regulations with limits],
            "standard_exclusions": [if query relates to exclusions]
        }
    """
    query_lower = query.lower()
    result = {"query": query, "definitions": [], "regulations": [], "standard_exclusions": []}

    # Search standard definitions
    for term, definition in IRDAI_KB["standard_definitions"].items():
        if query_lower in term.lower() or any(w in term.lower() for w in query_lower.split()):
            result["definitions"].append({
                "term": term.replace("_", " ").title(),
                "definition": definition
            })

    # Search mandated limits
    for key, limit_data in IRDAI_KB["mandated_limits"].items():
        if query_lower in key.lower() or query_lower in limit_data.get("description", "").lower():
            result["regulations"].append({
                "regulation": key.replace("_", " ").title(),
                **{k: v for k, v in limit_data.items()}
            })

    # Search room rent guidelines
    if any(w in query_lower for w in ["room", "rent", "accommodation"]):
        result["regulations"].append({
            "regulation": "Room Rent Guidelines",
            **IRDAI_KB["room_rent_guidelines"]
        })

    # Search copay guidelines
    if any(w in query_lower for w in ["copay", "co-pay", "co_pay", "cost sharing"]):
        result["regulations"].append({
            "regulation": "Co-Pay Guidelines",
            **IRDAI_KB["copay_guidelines"]
        })

    # Search exclusions
    if any(w in query_lower for w in ["exclusion", "excluded", "not covered"]):
        result["standard_exclusions"] = IRDAI_KB["standard_exclusions"]

    logger.info(f"[Tool:irdai_regulation_lookup] Query='{query}', found {len(result['definitions'])} defs, "
                f"{len(result['regulations'])} regs")
    return result


# --- Tool 4: Rule Validator ---

_REQUIRED_CATEGORIES = {
    "room_rent", "copay", "exclusion_permanent", "waiting_period_initial",
    "waiting_period_pec", "pre_post_hospitalization",
}

_SUSPICIOUS_PATTERNS = {
    "room_rent": {"limit_value_range": (0.1, 10), "unit": "percentage"},
    "copay": {"limit_value_range": (1, 50), "unit": "percentage"},
    "deductible": {"limit_value_range": (1000, 500000), "unit": "absolute"},
}


def rule_validator(rules: list[dict], sum_insured: float = 0) -> dict:
    """
    Validate extracted policy rules for completeness, accuracy, and consistency.
    
    Checks:
    1. Missing critical categories (every Indian policy should have room rent, copay, exclusions)
    2. Suspicious values (negative amounts, copay > 50%, room rent > 10% of SI)
    3. Duplicate rules
    4. Rules that conflict with IRDAI regulations (e.g., waiting period > 48 months)
    
    Returns:
        {
            "is_valid": bool,
            "total_rules": int,
            "issues": [{"severity": "critical|warning|info", "message": str}],
            "categories_found": [str],
            "categories_missing": [str]
        }
    """
    issues = []
    categories_found = set()
    seen_conditions = set()

    for i, rule in enumerate(rules):
        cat = rule.get("category", "unknown")
        categories_found.add(cat)

        # Check for duplicates
        cond_key = rule.get("condition", "").lower().strip()[:80]
        if cond_key in seen_conditions:
            issues.append({
                "severity": "warning",
                "message": f"Rule {i+1}: Possible duplicate — '{cond_key[:50]}...'"
            })
        seen_conditions.add(cond_key)

        # Check for suspicious values
        limit_val = rule.get("limit_value")
        if limit_val is not None:
            if limit_val < 0:
                issues.append({
                    "severity": "critical",
                    "message": f"Rule {i+1} ({cat}): Negative limit value: {limit_val}"
                })
            
            if cat in _SUSPICIOUS_PATTERNS:
                pattern = _SUSPICIOUS_PATTERNS[cat]
                min_v, max_v = pattern["limit_value_range"]
                if limit_val < min_v or limit_val > max_v:
                    issues.append({
                        "severity": "warning",
                        "message": f"Rule {i+1} ({cat}): Value {limit_val} outside typical range ({min_v}-{max_v})"
                    })

        # IRDAI compliance checks
        if cat in ("waiting_period_specific", "waiting_period_pec") and limit_val:
            if limit_val > 48:
                issues.append({
                    "severity": "critical",
                    "message": f"Rule {i+1}: Waiting period {limit_val} months exceeds IRDAI maximum of 48 months"
                })
        
        if cat == "waiting_period_initial" and limit_val:
            if limit_val > 30:
                issues.append({
                    "severity": "critical",
                    "message": f"Rule {i+1}: Initial waiting period {limit_val} days exceeds IRDAI maximum of 30 days"
                })

        # Check clause reference
        if not rule.get("clause_reference") or rule.get("clause_reference") == "Not specified":
            issues.append({
                "severity": "info",
                "message": f"Rule {i+1} ({cat}): No clause reference — may be hard to audit"
            })

    # Check missing categories
    categories_missing = _REQUIRED_CATEGORIES - categories_found
    for missing in categories_missing:
        issues.append({
            "severity": "warning",
            "message": f"Missing expected category: '{missing}' — most Indian policies include this"
        })

    is_valid = not any(i["severity"] == "critical" for i in issues)

    logger.info(f"[Tool:rule_validator] Validated {len(rules)} rules: "
                f"{len(issues)} issues, valid={is_valid}")
    return {
        "is_valid": is_valid,
        "total_rules": len(rules),
        "issues": issues,
        "categories_found": sorted(categories_found),
        "categories_missing": sorted(categories_missing),
    }
