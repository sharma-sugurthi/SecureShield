"""
Case Analysis Tools — Custom tools for the Case Agent.

Tools:
5. icd_procedure_lookup — Map procedure names to ICD codes with cost data
6. hospital_cost_estimator — Estimate costs by procedure, room, city
7. city_tier_classifier — Classify Indian cities into IRDAI tiers
8. medical_term_normalizer — Normalize medical abbreviations and terms
"""

import json
import logging
import re
from pathlib import Path
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Load knowledge bases
_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
with open(_KNOWLEDGE_DIR / "icd_procedures.json", "r") as f:
    ICD_KB = json.load(f)
with open(_KNOWLEDGE_DIR / "indian_cities.json", "r") as f:
    CITIES_KB = json.load(f)

# Build search index for procedures
_PROCEDURE_INDEX: dict[str, dict] = {}
for proc in ICD_KB["procedures"]:
    # Index by multiple keys for fuzzy matching
    key = proc["name"].lower()
    _PROCEDURE_INDEX[key] = proc
    # Also index by category
    words = key.split()
    for word in words:
        if len(word) > 4 and word not in ("with", "open", "total"):
            if word not in _PROCEDURE_INDEX:
                _PROCEDURE_INDEX[word] = proc

# Build search index for cities
_CITY_INDEX: dict[str, str] = {}
for tier, data in [("tier_1", CITIES_KB["tier_1"]), ("tier_2", CITIES_KB["tier_2"]), ("tier_3", CITIES_KB["tier_3"])]:
    city_list = data.get("cities", data.get("examples", []))
    for city in city_list:
        _CITY_INDEX[city.lower()] = tier


# --- Tool 5: ICD Procedure Lookup ---

def icd_procedure_lookup(procedure_name: str) -> dict:
    """
    Look up a medical procedure by name, returning ICD-10 code, typical costs,
    and insurance-relevant metadata.
    
    Args:
        procedure_name: Name of the procedure (can be partial or abbreviated)
    
    Returns:
        {
            "found": bool,
            "procedure": {name, icd_code, category, cost_ranges, typical_stay, waiting_period},
            "alternatives": [similar procedure names if not exact match]
        }
    """
    query = procedure_name.lower().strip()

    # Exact match
    if query in _PROCEDURE_INDEX:
        proc = _PROCEDURE_INDEX[query]
        return {"found": True, "procedure": _format_procedure(proc), "alternatives": []}

    # Partial match — check if any procedure name contains the query
    for key, proc in _PROCEDURE_INDEX.items():
        if query in key or key in query:
            return {"found": True, "procedure": _format_procedure(proc), "alternatives": []}

    # Fuzzy match — find closest procedure names
    all_names = [p["name"].lower() for p in ICD_KB["procedures"]]
    close = get_close_matches(query, all_names, n=3, cutoff=0.4)

    if close:
        # Return closest match with alternatives
        best_match = None
        for proc in ICD_KB["procedures"]:
            if proc["name"].lower() == close[0]:
                best_match = proc
                break

        return {
            "found": True,
            "procedure": _format_procedure(best_match) if best_match else None,
            "alternatives": close[1:] if len(close) > 1 else [],
            "match_type": "fuzzy",
        }

    logger.info(f"[Tool:icd_procedure_lookup] No match for '{procedure_name}'")
    return {
        "found": False,
        "procedure": None,
        "alternatives": [p["name"] for p in ICD_KB["procedures"][:5]],
        "message": f"Procedure '{procedure_name}' not found in database. Showing sample procedures."
    }


def _format_procedure(proc: dict) -> dict:
    """Format a procedure entry for tool output."""
    return {
        "name": proc["name"],
        "icd_code": proc["icd_code"],
        "category": proc["category"],
        "is_daycare": proc.get("is_daycare", False),
        "typical_stay_days": proc["typical_stay_days"],
        "cost_range": {
            "tier_1": proc["cost_range_tier1"],
            "tier_2": proc["cost_range_tier2"],
            "tier_3": proc["cost_range_tier3"],
        },
        "common_room_type": proc.get("common_room_type"),
        "waiting_period_applicable": proc.get("waiting_period_applicable", False),
        "typical_waiting_months": proc.get("typical_waiting_months"),
        "notes": proc.get("notes"),
    }


# --- Tool 6: Hospital Cost Estimator ---

# Room cost per day by type and tier (INR)
_ROOM_COSTS = {
    "general": {"tier_1": 1500, "tier_2": 800, "tier_3": 500},
    "semi_private": {"tier_1": 4000, "tier_2": 2500, "tier_3": 1500},
    "private": {"tier_1": 8000, "tier_2": 5000, "tier_3": 3000},
    "single_ac": {"tier_1": 10000, "tier_2": 6000, "tier_3": 4000},
    "deluxe": {"tier_1": 18000, "tier_2": 12000, "tier_3": 8000},
    "suite": {"tier_1": 30000, "tier_2": 20000, "tier_3": 15000},
    "icu": {"tier_1": 25000, "tier_2": 15000, "tier_3": 8000},
}


def hospital_cost_estimator(
    procedure: str,
    room_type: str = "semi_private",
    city_tier: str = "tier_1",
    stay_days: int | None = None,
) -> dict:
    """
    Estimate total hospital costs based on procedure, room type, and city tier.
    Uses real Indian hospital cost data.
    
    Args:
        procedure: Name of the medical procedure
        room_type: Room category (general, semi_private, private, single_ac, deluxe, suite, icu)
        city_tier: IRDAI city tier (tier_1, tier_2, tier_3)
        stay_days: Override for stay duration (uses typical if not provided)
    
    Returns:
        {
            "procedure_cost_estimate": {"low": float, "high": float, "median": float},
            "room_cost_per_day": float,
            "stay_days": int,
            "room_total": float,
            "estimated_total": {"low": float, "high": float, "median": float},
            "breakdown": {...}
        }
    """
    # Look up procedure costs
    proc_result = icd_procedure_lookup(procedure)
    
    if proc_result["found"] and proc_result["procedure"]:
        proc = proc_result["procedure"]
        cost_range = proc["cost_range"].get(city_tier, proc["cost_range"]["tier_1"])
        proc_low, proc_high = cost_range
        proc_median = (proc_low + proc_high) / 2
        
        if stay_days is None:
            stay_range = proc["typical_stay_days"]
            stay_days = (stay_range[0] + stay_range[1]) // 2 or 1
    else:
        # Unknown procedure — use conservative estimate
        tier_defaults = {"tier_1": (50000, 200000), "tier_2": (30000, 130000), "tier_3": (20000, 80000)}
        proc_low, proc_high = tier_defaults.get(city_tier, (50000, 200000))
        proc_median = (proc_low + proc_high) / 2
        if stay_days is None:
            stay_days = 3

    # Room cost
    room_type_lower = room_type.lower().replace("-", "_").replace(" ", "_")
    room_costs = _ROOM_COSTS.get(room_type_lower, _ROOM_COSTS["semi_private"])
    room_per_day = room_costs.get(city_tier, room_costs["tier_1"])
    room_total = room_per_day * stay_days

    # Additional costs estimate (10-20% of procedure cost for consumables, diagnostics)
    additional_low = proc_low * 0.10
    additional_high = proc_high * 0.20

    return {
        "procedure_cost_estimate": {
            "low": proc_low,
            "high": proc_high,
            "median": proc_median,
        },
        "room_cost_per_day": room_per_day,
        "room_type": room_type_lower,
        "stay_days": stay_days,
        "room_total": room_total,
        "additional_costs_estimate": {
            "low": additional_low,
            "high": additional_high,
        },
        "estimated_total": {
            "low": proc_low + room_total + additional_low,
            "high": proc_high + room_total + additional_high,
            "median": proc_median + room_total + (additional_low + additional_high) / 2,
        },
        "city_tier": city_tier,
        "source": "Indian hospital billing data 2024-25",
    }


# --- Tool 7: City Tier Classifier ---

def city_tier_classifier(city_or_hospital: str) -> dict:
    """
    Classify an Indian city or hospital into IRDAI tiers.
    
    Args:
        city_or_hospital: City name, hospital name, or address fragment
    
    Returns:
        {
            "tier": "tier_1" | "tier_2" | "tier_3",
            "confidence": "high" | "medium" | "low",
            "reasoning": str,
            "matched_on": str
        }
    """
    input_lower = city_or_hospital.lower().strip()

    # Check direct city match
    for city, tier in _CITY_INDEX.items():
        if city in input_lower or input_lower in city:
            return {
                "tier": tier,
                "confidence": "high",
                "reasoning": f"City '{city.title()}' is classified as {tier.replace('_', ' ').title()}",
                "matched_on": "city_name",
            }

    # Check hospital chain keywords
    for keyword, tier in CITIES_KB.get("hospital_keywords_to_tier", {}).items():
        if keyword in input_lower:
            return {
                "tier": tier,
                "confidence": "medium",
                "reasoning": f"Hospital chain '{keyword.title()}' typically operates in {tier.replace('_', ' ').title()} cities",
                "matched_on": "hospital_chain",
            }

    # Fuzzy city match
    all_cities = list(_CITY_INDEX.keys())
    close = get_close_matches(input_lower, all_cities, n=1, cutoff=0.6)
    if close:
        tier = _CITY_INDEX[close[0]]
        return {
            "tier": tier,
            "confidence": "medium",
            "reasoning": f"Closest match: '{close[0].title()}' ({tier.replace('_', ' ').title()})",
            "matched_on": "fuzzy_city_name",
        }

    # Default to tier_2 (conservative estimate)
    return {
        "tier": "tier_2",
        "confidence": "low",
        "reasoning": f"Could not classify '{city_or_hospital}'. Defaulting to Tier 2 (conservative estimate).",
        "matched_on": "default",
    }


# --- Tool 8: Medical Term Normalizer ---
# Comprehensive abbreviation map with 150+ medical terms (Indian healthcare context)

_ABBREVIATION_MAP = {
    # === SURGICAL PROCEDURES (50+) ===
    # General Surgery
    "lap chole": "Laparoscopic Cholecystectomy",
    "open chole": "Open Cholecystectomy",
    "lap appy": "Laparoscopic Appendectomy",
    "open appy": "Open Appendectomy",
    "hernia repair": "Hernia Repair",
    "ventral hernia": "Ventral Hernia Repair",
    
    # Obstetric & Gynecology
    "lscs": "Lower Segment Caesarean Section",
    "cs": "Caesarean Section",
    "c-section": "Caesarean Section",
    "d&c": "Dilation and Curettage",
    "hysterectomy": "Hysterectomy",
    "tubectomy": "Tubectomy",
    "iud insertion": "Intrauterine Device Insertion",
    
    # Cardiac & Thoracic
    "cabg": "Coronary Artery Bypass Graft",
    "ptca": "Percutaneous Transluminal Coronary Angioplasty",
    "pci": "Percutaneous Coronary Intervention",
    "stent placement": "Stent Placement",
    "avr": "Aortic Valve Replacement",
    "mitral valve": "Mitral Valve Repair/Replacement",
    
    # Urology
    "turp": "Transurethral Resection of Prostate",
    "pcnl": "Percutaneous Nephrolithotomy",
    "eswl": "Extracorporeal Shock Wave Lithotripsy",
    "ureteric stent": "Ureteric Stent Placement",
    "circumcision": "Circumcision",
    
    # Orthopedic
    "tkr": "Total Knee Replacement",
    "thr": "Total Hip Replacement",
    "acl": "Anterior Cruciate Ligament Reconstruction",
    "pcl reconstruction": "Posterior Cruciate Ligament Reconstruction",
    "rotator cuff": "Rotator Cuff Repair",
    "arthroscopy": "Arthroscopic Surgery",
    "meniscectomy": "Meniscectomy",
    "joint replacement": "Joint Replacement Surgery",
    
    # GI & Hepatobiliary
    "ercp": "Endoscopic Retrograde Cholangiopancreatography",
    "esd": "Endoscopic Submucosal Dissection",
    "gastric bypass": "Gastric Bypass Surgery",
    "liver resection": "Liver Resection",
    "splenectomy": "Splenectomy",
    
    # ENT Surgery
    "fess": "Functional Endoscopic Sinus Surgery",
    "tonsillectomy": "Tonsillectomy",
    "adenoidectomy": "Adenoidectomy",
    "thyroidectomy": "Thyroidectomy",
    "mastoidectomy": "Mastoidectomy",
    "myringotomy": "Myringotomy",
    
    # Neurosurgery
    "craniotomy": "Craniotomy",
    "laminectomy": "Laminectomy",
    "spinal fusion": "Spinal Fusion",
    "discectomy": "Discectomy",
    "aneurysm clipping": "Aneurysm Clipping",
    
    # Oncologic
    "mastectomy": "Mastectomy",
    "lumpectomy": "Lumpectomy",
    "colostomy": "Colostomy",
    "ileostomy": "Ileostomy",
    
    # === DIAGNOSTIC PROCEDURES (15+) ===
    "endoscopy": "Endoscopy",
    "colonoscopy": "Colonoscopy",
    "ct scan": "CT Scan",
    "mri": "Magnetic Resonance Imaging",
    "ultrasound": "Ultrasound",
    "echo": "Echocardiography",
    "ekg": "Electrocardiography",
    "ecg": "Electrocardiography",
    "angiography": "Coronary Angiography",
    "biopsy": "Biopsy",
    "pap smear": "Pap Smear",
    "mammography": "Mammography",
    "xray": "X-Ray",
    "x-ray": "X-Ray",
    
    # === MEDICAL CONDITIONS & DISEASES (50+) ===
    # Endocrine
    "dm": "Diabetes Mellitus",
    "dm1": "Type 1 Diabetes Mellitus",
    "dm2": "Type 2 Diabetes Mellitus",
    "t1dm": "Type 1 Diabetes Mellitus",
    "t2dm": "Type 2 Diabetes Mellitus",
    "gestational diabetes": "Gestational Diabetes",
    "thyroid": "Thyroid Disorder",
    "hyperthyroid": "Hyperthyroidism",
    "hypothyroid": "Hypothyroidism",
    
    # Cardiovascular
    "htn": "Hypertension",
    "hypertension": "Hypertension",
    "hbp": "High Blood Pressure",
    "ihd": "Ischemic Heart Disease",
    "cad": "Coronary Artery Disease",
    "acs": "Acute Coronary Syndrome",
    "ami": "Acute Myocardial Infarction",
    "mi": "Myocardial Infarction",
    "angina": "Angina Pectoris",
    "chf": "Congestive Heart Failure",
    "hf": "Heart Failure",
    "arrhythmia": "Cardiac Arrhythmia",
    "afib": "Atrial Fibrillation",
    "dvt": "Deep Vein Thrombosis",
    "pe": "Pulmonary Embolism",
    "stroke": "Cerebrovascular Accident",
    "cva": "Cerebrovascular Accident",
    "hypertensive crisis": "Hypertensive Crisis",
    "cardiogenic shock": "Cardiogenic Shock",
    
    # Respiratory
    "copd": "Chronic Obstructive Pulmonary Disease",
    "asthma": "Bronchial Asthma",
    "pneumonia": "Pneumonia",
    "tuberculosis": "Tuberculosis",
    "tb": "Tuberculosis",
    "bronchitis": "Bronchitis",
    "pleurisy": "Pleurisy",
    "pneumothorax": "Pneumothorax",
    "ards": "Acute Respiratory Distress Syndrome",
    
    # Gastrointestinal
    "gerd": "Gastroesophageal Reflux Disease",
    "peptic ulcer": "Peptic Ulcer Disease",
    "ibd": "Inflammatory Bowel Disease",
    "hepatitis": "Hepatitis",
    "cirrhosis": "Cirrhosis",
    "gastritis": "Gastritis",
    "pancreatitis": "Pancreatitis",
    "appendicitis": "Appendicitis",
    "cholecystitis": "Cholecystitis",
    "kidney stones": "Nephrolithiasis",
    "gallstones": "Cholelithiasis",
    "ugib": "Upper GI Bleed",
    "lgib": "Lower GI Bleed",
    
    # Renal & Urinary
    "ckd": "Chronic Kidney Disease",
    "esrd": "End Stage Renal Disease",
    "uti": "Urinary Tract Infection",
    "bph": "Benign Prostatic Hyperplasia",
    "prostatitis": "Prostatitis",
    
    # Rheumatologic & Musculoskeletal
    "ra": "Rheumatoid Arthritis",
    "oa": "Osteoarthritis",
    "sle": "Systemic Lupus Erythematosus",
    "sjögren's": "Sjögren's Syndrome",
    "spondylitis": "Ankylosing Spondylitis",
    "fibromyalgia": "Fibromyalgia",
    "gout": "Gout",
    "osteoporosis": "Osteoporosis",
    
    # Infectious
    "hiv": "Human Immunodeficiency Virus",
    "hepatitis b": "Hepatitis B",
    "hepatitis c": "Hepatitis C",
    "malaria": "Malaria",
    "dengue": "Dengue Fever",
    "covid": "COVID-19",
    "covid-19": "COVID-19",
    
    # Hematologic
    "anemia": "Anemia",
    "leukemia": "Leukemia",
    "lymphoma": "Lymphoma",
    "sickle cell": "Sickle Cell Disease",
    "thrombocytopenia": "Thrombocytopenia",
    
    # Neurologic
    "epilepsy": "Epilepsy",
    "seizure": "Seizure Disorder",
    "parkinson's": "Parkinson's Disease",
    "alzheimer's": "Alzheimer's Disease",
    "migraine": "Migraine",
    "meningitis": "Meningitis",
    "encephalitis": "Encephalitis",
    
    # Psychiatric
    "depression": "Depression",
    "anxiety": "Anxiety Disorder",
    "bipolar": "Bipolar Disorder",
    "schizophrenia": "Schizophrenia",
    
    # Obstetric
    "pregnancy": "Pregnancy",
    "preeclampsia": "Preeclampsia",
    "eclampsia": "Eclampsia",
    
    # Oncologic
    "cancer": "Cancer/Malignancy",
    "breast cancer": "Breast Cancer",
    "lung cancer": "Lung Cancer",
    "colon cancer": "Colorectal Cancer",
    "prostate cancer": "Prostate Cancer",
    "cervical cancer": "Cervical Cancer",
    
    # === ROOM TYPES & LOCATION (25+) ===
    "general": "General Ward",
    "general ward": "General Ward",
    "gen ward": "General Ward",
    "ward": "General Ward",
    "semi-private": "Semi-Private Room",
    "semi private": "Semi-Private Room",
    "semi_private": "Semi-Private Room",
    "sharing": "Semi-Private Room",
    "twin sharing": "Semi-Private Room",
    "two bed": "Semi-Private Room",
    "private": "Private Room",
    "pvt": "Private Room",
    "pvt room": "Private Room",
    "private room": "Private Room",
    "single": "Single AC Room",
    "single ac": "Single AC Room",
    "single a/c": "Single AC Room",
    "ac room": "Single AC Room",
    "air conditioned": "Single AC Room",
    "deluxe": "Deluxe Room",
    "deluxe room": "Deluxe Room",
    "suite": "Executive Suite",
    "executive suite": "Executive Suite",
    "presidential": "Executive Suite",
    "icu": "ICU Room",
    "intensive care": "ICU Room",
    "critical care": "ICU Room",
    "high dependency": "High Dependency Unit",
    "hdu": "High Dependency Unit",
    
    # === ADMISSION TYPES ===
    "planned": "Planned Admission",
    "elective": "Planned Admission",
    "scheduled": "Planned Admission",
    "emergency": "Emergency Admission",
    "urgent": "Emergency Admission",
    "accident": "Emergency Admission",
}


def medical_term_normalizer(text: str) -> dict:
    """
    Normalize medical terms, abbreviations, and shorthand in clinical text.
    Purely local operation — no LLM calls.
    
    Args:
        text: Raw clinical text with possible abbreviations
    
    Returns:
        {
            "original": str,
            "normalized": str,
            "resolved_abbreviations": [{"abbrev": str, "expanded": str}],
            "detected_conditions": [str],
            "detected_procedure": str | None
        }
    """
    text_lower = text.lower().strip()
    normalized = text
    resolved = []
    conditions = []
    procedure = None

    # === Step 1: Resolve abbreviations (word-boundary matching) ===
    for abbrev, expanded in _ABBREVIATION_MAP.items():
        if abbrev in text_lower:
            # Check word boundary (not substring) — case insensitive
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            if re.search(pattern, text_lower):
                normalized = re.sub(pattern, expanded, normalized, flags=re.IGNORECASE)
                resolved.append({"abbrev": abbrev.upper(), "expanded": expanded})

    # === Step 2: Detect known conditions (expanded) ===
    condition_keywords = {
        # Endocrine
        "diabetes": "Diabetes Mellitus",
        "diabetic": "Diabetes Mellitus",
        "hyperglycemia": "Hyperglycemia",
        "hypoglycemia": "Hypoglycemia",
        "thyroid": "Thyroid Disorder",
        "hyperthyroid": "Hyperthyroidism",
        "hypothyroid": "Hypothyroidism",
        
        # Cardiovascular
        "hypertension": "Hypertension",
        "high blood pressure": "Hypertension",
        "coronary": "Coronary Artery Disease",
        "heart disease": "Heart Disease",
        "angina": "Angina Pectoris",
        "heart failure": "Heart Failure",
        "cardiac": "Cardiac Disorder",
        "arrhythmia": "Arrhythmia",
        "atrial fibrillation": "Atrial Fibrillation",
        "myocardial infarction": "Myocardial Infarction",
        "thrombosis": "Thrombosis",
        "clot": "Thrombosis",
        
        # Respiratory
        "asthma": "Asthma",
        "copd": "COPD",
        "pneumonia": "Pneumonia",
        "tuberculosis": "Tuberculosis",
        "bronchitis": "Bronchitis",
        "emphysema": "Emphysema",
        
        # Gastrointestinal
        "gerd": "GERD",
        "reflux": "Gastroesophageal Reflux",
        "ulcer": "Peptic Ulcer Disease",
        "gastritis": "Gastritis",
        "hepatitis": "Hepatitis",
        "cirrhosis": "Cirrhosis",
        "pancreatitis": "Pancreatitis",
        "appendicitis": "Appendicitis",
        "gallstone": "Cholelithiasis",
        "kidney stone": "Nephrolithiasis",
        "colitis": "Colitis",
        
        # Renal
        "kidney disease": "Kidney Disease",
        "chronic kidney": "Chronic Kidney Disease",
        "renal failure": "Renal Failure",
        "urinary": "Urinary Disorder",
        "kidney": "Kidney Disease",
        
        # Rheumatologic
        "arthritis": "Arthritis",
        "rheumatoid": "Rheumatoid Arthritis",
        "osteoarthritis": "Osteoarthritis",
        "joint": "Joint Disorder",
        "lupus": "Systemic Lupus Erythematosus",
        "gout": "Gout",
        "osteoporosis": "Osteoporosis",
        
        # Infectious
        "infection": "Infection",
        "fever": "Fever",
        "malaria": "Malaria",
        "dengue": "Dengue Fever",
        "typhoid": "Typhoid",
        "hiv": "HIV",
        "hepatitis": "Hepatitis",
        "tuberculosis": "Tuberculosis",
        "covid": "COVID-19",
        
        # Neurologic
        "epilepsy": "Epilepsy",
        "seizure": "Seizure Disorder",
        "stroke": "Cerebrovascular Accident",
        "migraine": "Migraine",
        "headache": "Headache",
        "parkinson": "Parkinson's Disease",
        "alzheimer": "Alzheimer's Disease",
        
        # Hematologic
        "anemia": "Anemia",
        "leukemia": "Leukemia",
        "lymphoma": "Lymphoma",
        "cancer": "Cancer/Malignancy",
        "tumor": "Tumor",
        "malignancy": "Malignancy",
        
        # Psychiatric
        "depression": "Depression",
        "anxiety": "Anxiety Disorder",
        "bipolar": "Bipolar Disorder",
        
        # Obstetric
        "pregnancy": "Pregnancy",
        "pregnant": "Pregnancy",
        "preeclampsia": "Preeclampsia",
        "eclampsia": "Eclampsia",
    }
    
    for keyword, condition in condition_keywords.items():
        if keyword in text_lower and condition not in conditions:
            conditions.append(condition)

    # === Step 3: Try to identify primary procedure ===
    proc_result = icd_procedure_lookup(normalized)
    if proc_result.get("found") and proc_result.get("procedure"):
        procedure = proc_result["procedure"]["name"]

    logger.info(f"[Tool:medical_term_normalizer] Resolved {len(resolved)} abbreviations, "
                f"detected {len(conditions)} conditions, identified procedure: {procedure or 'unknown'}")
    
    return {
        "original": text,
        "normalized": normalized,
        "resolved_abbreviations": resolved,
        "detected_conditions": conditions,
        "detected_procedure": procedure,
    }
