#!/usr/bin/env python3
"""
TASK 4: Demo Seeding Script
Pre-populates database with 3 reference health insurance policies.

This script enables instant demo operations by seeding the cache with:
1. Star Health Insurance - Comprehensive Health Plan
2. ICICI Lombard - Basic Shield Plan  
3. ICICI Lombard - Dispute Case (for grievance demo)

Usage:
    python3 seed_demo.py              # Seed demo (safe, checks for existing)
    python3 seed_demo.py --reset      # Clear cache and re-seed
    python3 seed_demo.py --list       # List seeded policies
"""

import sys
import os
import hashlib
import asyncio
import json
from pathlib import Path
from typing import List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db.database import init_db, save_policy, get_policy_by_hash, get_all_policies, clear_policies_and_checks


# ============================================================================
# DEMO POLICY DEFINITIONS
# ============================================================================

DEMO_POLICIES = [
    {
        "name": "Star Health Insurance - Comprehensive Plan",
        "pdf_content": """
            STAR HEALTH INSURANCE COMPANY LIMITED
            STAR HEALTH COMPREHENSIVE PLAN
            
            Policy Document and Schedule
            
            INSURER: Star Health Insurance Company Limited
            PLAN NAME: Star Comprehensive Health Plan
            SUM INSURED: ₹1,000,000
            POLICY TYPE: Individual
            
            SECTION 1: COVERAGE AND BENEFITS
            1.1 Room Rent: Semi-private room maximum ₹5,000 per day
            1.2 ICU Charges: 100% covered (normal ICU and CCU)
            1.3 Cashless Hospitalization: Available at 5000+ empaneled hospitals
            1.4 Surgery: 100% coverage for in-patient procedures
            1.5 Day-care Procedures: Covered up to ₹50,000
            
            SECTION 2: EXCLUSIONS AND LIMITS
            2.1 Pre-existing conditions: 48-month waiting period (waived if declared)
            2.2 Maternity: Covered after 12 months waiting period, max ₹250,000
            2.3 Mental illness: Covered from 3rd year onwards
            2.4 Organ transplant: Covered, max ₹500,000
            2.5 Alternative therapy: Covered for 30 days per year, max ₹10,000
            
            SECTION 3: DEDUCTIBLES AND CO-PAYMENTS
            3.1 Annual deductible: Nil
            3.2 Co-payment: 5% on in-patient claims above ₹50,000
            3.3 Co-insurance: 10% for network hospitals during normal hours
        """,
        "rules": [
            {
                "category": "room_rent",
                "condition": "Semi-private room maximum per day",
                "limit_type": "sublimit",
                "limit_value": 5000,
                "clause_reference": "Section 1.1",
                "applies_to": "all"
            },
            {
                "category": "icu",
                "condition": "ICU charges 100% covered for normal and CCU",
                "limit_type": "percentage",
                "limit_value": 100,
                "clause_reference": "Section 1.2",
                "applies_to": "all"
            },
            {
                "category": "pre_existing",
                "condition": "Pre-existing conditions covered after 48 months",
                "limit_type": "waiting_period",
                "limit_value": 48,
                "clause_reference": "Section 2.1",
                "applies_to": "all"
            },
            {
                "category": "maternity",
                "condition": "Maternity coverage after 12 months, max sum",
                "limit_type": "sublimit",
                "limit_value": 250000,
                "clause_reference": "Section 2.2",
                "applies_to": "all"
            },
            {
                "category": "copay",
                "condition": "5% co-payment on in-patient claims above 50k",
                "limit_type": "copay",
                "limit_value": 5.0,
                "clause_reference": "Section 3.2",
                "applies_to": "inpatient"
            },
            {
                "category": "deductible",
                "condition": "No annual deductible",
                "limit_type": "absolute",
                "limit_value": 0,
                "clause_reference": "Section 3.1",
                "applies_to": "all"
            },
        ],
        "insurer": "Star Health Insurance Company Limited",
        "plan_name": "Star Comprehensive Health Plan",
        "sum_insured": 1000000,
        "policy_type": "individual"
    },
    {
        "name": "ICICI Lombard - Basic Shield Plan",
        "pdf_content": """
            ICICI LOMBARD GENERAL INSURANCE COMPANY LIMITED
            BASIC SHIELD HEALTH INSURANCE PLAN
            
            Policy Document
            
            INSURER: ICICI Lombard General Insurance Company Limited
            PLAN NAME: Basic Shield Health Plan
            SUM INSURED: ₹500,000
            POLICY TYPE: Family
            
            SECTION 1: COVERAGE
            1.1 Hospitalization: Full coverage for in-patient treatment
            1.2 Room category: Up to general ward or semi-private
            1.3 Maximum room rent: ₹3,000 per day
            1.4 Emergency care: Covered for 24 hours prior to admission
            1.5 Intensive care: ICU charges covered at 100%
            
            SECTION 2: SUB-LIMITS
            2.1 Day-care procedures: Maximum ₹30,000 per procedure
            2.2 Mental illness: Covered from 1st year onwards
            2.3 Organ transplant: Covered up to ₹300,000
            2.4 Bariatric surgery: Covered up to ₹200,000
            
            SECTION 3: EXCLUSIONS
            3.1 Waiting period for specific illnesses: 30 days
            3.2 Pre-existing conditions: 24-month waiting period
            3.3 Pregnancy and childbirth: Covered after 9 months
            3.4 Alcohol-related diseases: Excluded
            
            SECTION 4: CLAIM PROVISIONS
            4.1 Claim settlement: Within 15 days of document receipt
            4.2 Deductible: ₹5,000 per claim
            4.3 Co-insurance: 20% of admissible amount
        """,
        "rules": [
            {
                "category": "room_rent",
                "condition": "General or semi-private maximum 3000 per day",
                "limit_type": "sublimit",
                "limit_value": 3000,
                "clause_reference": "Section 1.3",
                "applies_to": "all"
            },
            {
                "category": "day_care",
                "condition": "Day-care procedures maximum per procedure",
                "limit_type": "sublimit",
                "limit_value": 30000,
                "clause_reference": "Section 2.1",
                "applies_to": "all"
            },
            {
                "category": "pre_existing",
                "condition": "Pre-existing conditions 24-month waiting period",
                "limit_type": "waiting_period",
                "limit_value": 24,
                "clause_reference": "Section 3.2",
                "applies_to": "all"
            },
            {
                "category": "deductible",
                "condition": "Deductible per claim",
                "limit_type": "absolute",
                "limit_value": 5000,
                "clause_reference": "Section 4.2",
                "applies_to": "all"
            },
            {
                "category": "coinsurance",
                "condition": "Co-insurance 20% of admissible",
                "limit_type": "coinsurance",
                "limit_value": 20.0,
                "clause_reference": "Section 4.3",
                "applies_to": "all"
            },
        ],
        "insurer": "ICICI Lombard General Insurance Company Limited",
        "plan_name": "Basic Shield Health Plan",
        "sum_insured": 500000,
        "policy_type": "family"
    },
    {
        "name": "ICICI Lombard - Dispute Reference Case",
        "pdf_content": """
            ICICI LOMBARD GENERAL INSURANCE COMPANY LIMITED
            COMPREHENSIVE HEALTH POLICY
            
            CASE REFERENCE FOR DISPUTE HANDLING
            
            INSURER: ICICI Lombard General Insurance Company Limited
            PLAN NAME: Comprehensive Family Coverage
            SUM INSURED: ₹750,000
            POLICY TYPE: Family
            
            SECTION 1: POLICY BENEFITS
            1.1 In-patient hospitalization: Full coverage
            1.2 Room rent limit: ₹4,000 per day (semi-private)
            1.3 ICU care: 100% coverage
            1.4 Surgery and procedures: 100% coverage
            1.5 Emergency care: 24-hour prior to admission
            
            SECTION 2: SPECIFIC CONDITIONS
            2.1 Diabetes mellitus: Covered with 6-month waiting period
            2.2 Hypertension: Covered from day 1
            2.3 Heart disease: 12-month waiting period (if pre-existing)
            2.4 Cancer treatment: Covered, maximum ₹400,000
            
            SECTION 3: GRIEVANCE PROVISIONS
            3.1 Claim rejection rationale: Provided within 7 days
            3.2 Appeal mechanism: Two-tier grievance process
            3.3 IRDAI complaint procedure: Available within 30 days
            3.4 Claim review: Mandatory review if amount exceeds ₹1,00,000
            
            SECTION 4: CLAIM SETTLEMENT
            4.1 Settlement within 30 days of full documentation
            4.2 Partial approvals permitted with detailed justification
            4.3 Interest on delayed payment: 24% per annum after 30 days
        """,
        "rules": [
            {
                "category": "room_rent",
                "condition": "Semi-private room maximum 4000 per day",
                "limit_type": "sublimit",
                "limit_value": 4000,
                "clause_reference": "Section 1.2",
                "applies_to": "all"
            },
            {
                "category": "diabetes",
                "condition": "Diabetes covered after 6-month waiting period",
                "limit_type": "waiting_period",
                "limit_value": 6,
                "clause_reference": "Section 2.1",
                "applies_to": "all"
            },
            {
                "category": "cancer",
                "condition": "Cancer treatment covered maximum amount",
                "limit_type": "sublimit",
                "limit_value": 400000,
                "clause_reference": "Section 2.4",
                "applies_to": "all"
            },
            {
                "category": "grievance_timeline",
                "condition": "Claim rejection details within 7 days",
                "limit_type": "timeline",
                "limit_value": 7,
                "clause_reference": "Section 3.1",
                "applies_to": "all"
            },
            {
                "category": "claim_settlement",
                "condition": "Settlement within 30 days of full documentation",
                "limit_type": "timeline",
                "limit_value": 30,
                "clause_reference": "Section 4.1",
                "applies_to": "all"
            },
        ],
        "insurer": "ICICI Lombard General Insurance Company Limited",
        "plan_name": "Comprehensive Family Coverage",
        "sum_insured": 750000,
        "policy_type": "family"
    }
]


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================

async def seed_policy(policy_def: dict) -> tuple:
    """
    Seed a single policy into the database.
    
    Returns: (policy_id, pdf_hash)
    """
    # Compute PDF hash (encode unicode to UTF-8 bytes)
    pdf_hash = hashlib.sha256(policy_def["pdf_content"].encode("utf-8")).hexdigest()
    
    # Check if already seeded
    existing = await get_policy_by_hash(pdf_hash)
    if existing:
        return existing["id"], pdf_hash, "EXISTING"
    
    # Save new policy
    policy_id = await save_policy(
        insurer=policy_def["insurer"],
        plan_name=policy_def["plan_name"],
        sum_insured=policy_def["sum_insured"],
        policy_type=policy_def["policy_type"],
        rules=policy_def["rules"],
        raw_text_hash=pdf_hash
    )
    
    return policy_id, pdf_hash, "NEW"


async def seed_all_policies() -> dict:
    """
    Seed all demo policies. Returns summary statistics.
    """
    await init_db()
    
    results = {
        "total": len(DEMO_POLICIES),
        "new": 0,
        "existing": 0,
        "policies": []
    }
    
    for policy_def in DEMO_POLICIES:
        policy_id, pdf_hash, status = await seed_policy(policy_def)
        
        results["policies"].append({
            "id": policy_id,
            "name": policy_def["plan_name"],
            "insurer": policy_def["insurer"],
            "hash": pdf_hash[:12] + "...",
            "status": status,
            "rules": len(policy_def["rules"])
        })
        
        if status == "NEW":
            results["new"] += 1
        else:
            results["existing"] += 1
    
    return results


async def reset_and_seed():
    """
    Clear existing policies and re-seed demo data.
    """
    await init_db()
    # Clear database via async ORM helper
    await clear_policies_and_checks()
    print("✓ Database cleared")
    # Re-seed
    results = await seed_all_policies()
    return results


async def list_policies():
    """
    List all seeded policies in database.
    """
    await init_db()
    policies = await get_all_policies()
    return policies


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="TASK 4: Seed demo data for instant SecureShield operation"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear database and re-seed all demo policies"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all seeded policies in database"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("TASK 4: Demo Seeding Script")
    print("="*80)
    
    try:
        if args.reset:
            print("\n⚠️  Resetting database and re-seeding demo data...")
            results = await reset_and_seed()
            
            print(f"\n✓ Database reset and re-seeded")
            print(f"  Total policies: {results['total']}")
            print(f"  New policies: {results['new']}")
            print(f"  Existing policies: {results['existing']}")
            
        elif args.list:
            print("\n📋 Seeded Policies in Database:")
            policies = await list_policies()
            
            if not policies:
                print("  (No policies seeded)")
            else:
                for i, policy in enumerate(policies, 1):
                    print(f"\n  [{i}] Policy #{policy['id']}")
                    print(f"      Insurer: {policy['insurer']}")
                    print(f"      Plan: {policy['plan_name']}")
                    print(f"      Sum Insured: ₹{policy['sum_insured']:,.0f}")
                    print(f"      Type: {policy['policy_type']}")
                    print(f"      Created: {policy['created_at']}")
            
        else:
            # Default: seed without clearing
            print("\n📦 Seeding demo policies (checking for existing data)...")
            results = await seed_all_policies()
            
            print(f"\n✓ Seeding complete")
            print(f"  Total policies: {results['total']}")
            print(f"  New policies seeded: {results['new']}")
            print(f"  Existing policies: {results['existing']}")
        
        # Print detailed results
        print("\n" + "-"*80)
        print("Seeded Policies:")
        print("-"*80)
        for policy in results["policies"]:
            print(f"\n✓ {policy['name']}")
            print(f"  Policy ID: #{policy['id']}")
            print(f"  Insurer: {policy['insurer']}")
            print(f"  Hash: {policy['hash']}")
            print(f"  Rules: {policy['rules']}")
            print(f"  Status: {policy['status']}")
        
        print("\n" + "="*80)
        print("✅ TASK 4: Demo Seeding Complete")
        print("="*80)
        
        print("""
Demo Benefits:
  ✓ 3 reference policies pre-seeded in cache
  ✓ Instant policy uploads without LLM calls
  ✓ Demo operations at 100% speed (zero API latency)
  ✓ Perfect for testing and demonstrations
  
Usage:
  python3 scripts/seed_demo.py              # Seed demo (safe)
  python3 scripts/seed_demo.py --reset      # Clear and re-seed
  python3 scripts/seed_demo.py --list       # List seeded policies
""")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
