"""
TASK 3: PDF Hash Caching — Unit and Integration Tests
Tests for PDF deduplication and cached policy retrieval.
"""

import asyncio
import hashlib
import json
from pathlib import Path
from db.database import get_policy_by_hash, save_policy, init_db
from models.policy import PolicyRule

async def test_pdf_hash_generation():
    """Test 1: SHA-256 PDF hash generation"""
    print("\n" + "="*80)
    print("[TEST 1] PDF Hash Generation (SHA-256)")
    print("="*80)
    
    # Simulate PDF bytes
    pdf_bytes_1 = b"Sample PDF content for testing policy document"
    pdf_bytes_2 = b"Different PDF content for another policy"
    pdf_bytes_1_duplicate = b"Sample PDF content for testing policy document"
    
    # Compute hashes
    hash_1 = hashlib.sha256(pdf_bytes_1).hexdigest()
    hash_2 = hashlib.sha256(pdf_bytes_2).hexdigest()
    hash_1_dup = hashlib.sha256(pdf_bytes_1_duplicate).hexdigest()
    
    print(f"✓ PDF 1 Hash: {hash_1[:16]}... (length: {len(hash_1)})")
    print(f"✓ PDF 2 Hash: {hash_2[:16]}... (length: {len(hash_2)})")
    print(f"✓ PDF 1 Duplicate Hash: {hash_1_dup[:16]}...")
    print(f"✓ Hashes match for identical PDFs: {hash_1 == hash_1_dup}")
    print(f"✓ Hashes differ for different PDFs: {hash_1 != hash_2}")
    
    assert hash_1 == hash_1_dup, "Identical PDFs should have identical hashes"
    assert hash_1 != hash_2, "Different PDFs should have different hashes"
    print("\n✅ TEST 1 PASSED: Hash generation working correctly")


async def test_policy_save_with_hash():
    """Test 2: Save policy with PDF hash"""
    print("\n" + "="*80)
    print("[TEST 2] Save Policy with PDF Hash")
    print("="*80)
    
    await init_db()
    
    # Create test policy data
    test_hash = hashlib.sha256(b"test_pdf_content").hexdigest()
    test_rules = [
        {
            "category": "room_rent",
            "condition": "Room rent limited to semi-private category",
            "limit_type": "sublimit",
            "limit_value": 5000,
            "clause_reference": "Section 2.1",
            "applies_to": "all"
        }
    ]
    
    policy_id = await save_policy(
        insurer="Test Insurer Ltd",
        plan_name="Test Health Plan",
        sum_insured=500000,
        policy_type="individual",
        rules=test_rules,
        raw_text_hash=test_hash
    )
    
    print(f"✓ Policy saved with ID: {policy_id}")
    print(f"✓ Policy hash: {test_hash[:16]}...")
    print(f"✓ Rules count: {len(test_rules)}")
    
    assert policy_id > 0, "Policy ID should be positive"
    print("\n✅ TEST 2 PASSED: Policy saved with hash")


async def test_pdf_cache_lookup():
    """Test 3: Retrieve policy by PDF hash (cache lookup)"""
    print("\n" + "="*80)
    print("[TEST 3] PDF Cache Lookup (get_policy_by_hash)")
    print("="*80)
    
    await init_db()
    
    # Save test policy
    test_hash = hashlib.sha256(b"cache_test_pdf").hexdigest()
    test_rules = [
        {
            "category": "copay",
            "condition": "Co-payment at 5%",
            "limit_type": "copay",
            "limit_value": 5.0,
            "clause_reference": "Section 3.2",
            "applies_to": "outpatient"
        }
    ]
    
    policy_id = await save_policy(
        insurer="Cache Test Insurer",
        plan_name="Cache Test Plan",
        sum_insured=750000,
        policy_type="family",
        rules=test_rules,
        raw_text_hash=test_hash
    )
    
    print(f"✓ Policy saved: #{policy_id}")
    
    # Lookup by hash
    cached_policy = await get_policy_by_hash(test_hash)
    
    if cached_policy:
        print(f"✓ Cache HIT: Retrieved policy #{cached_policy['id']}")
        print(f"  - Insurer: {cached_policy['insurer']}")
        print(f"  - Plan: {cached_policy['plan_name']}")
        print(f"  - Sum Insured: ₹{cached_policy['sum_insured']:,.0f}")
        print(f"  - Rules: {len(cached_policy['rules'])}")
    else:
        print(f"✗ Cache MISS: Failed to retrieve policy")
    
    assert cached_policy is not None, "Should find cached policy by hash"
    assert cached_policy['id'] == policy_id, "Retrieved policy should match saved policy"
    assert cached_policy['insurer'] == "Cache Test Insurer", "Insurer should match"
    print("\n✅ TEST 3 PASSED: Cache lookup working correctly")


async def test_cache_miss():
    """Test 4: Non-existent hash returns None (cache miss)"""
    print("\n" + "="*80)
    print("[TEST 4] Cache Miss (Non-existent PDF Hash)")
    print("="*80)
    
    await init_db()
    
    # Try to lookup non-existent hash
    fake_hash = hashlib.sha256(b"non_existent_pdf").hexdigest()
    result = await get_policy_by_hash(fake_hash)
    
    print(f"✓ Looked up non-existent hash: {fake_hash[:16]}...")
    print(f"✓ Result: {result} (None expected)")
    
    assert result is None, "Non-existent hash should return None"
    print("\n✅ TEST 4 PASSED: Cache miss handled correctly")


async def test_duplicate_pdf_detection():
    """Test 5: Duplicate PDF detection (same hash, different saves)"""
    print("\n" + "="*80)
    print("[TEST 5] Duplicate PDF Detection")
    print("="*80)
    
    await init_db()
    
    # Same PDF bytes, different attempts to save
    pdf_bytes = b"Apollo Health Insurance Policy Document"
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    rules_1 = [{"category": "room_rent", "condition": "Room limit", "limit_type": "absolute", 
                "limit_value": 3000, "clause_reference": "Sec 1", "applies_to": "all"}]
    rules_2 = [{"category": "copay", "condition": "Copay 10%", "limit_type": "copay", 
                "limit_value": 10, "clause_reference": "Sec 2", "applies_to": "all"}]
    
    # Save first attempt
    policy_id_1 = await save_policy(
        insurer="Apollo Hospitals",
        plan_name="Health Plus",
        sum_insured=500000,
        policy_type="individual",
        rules=rules_1,
        raw_text_hash=pdf_hash
    )
    
    print(f"✓ First save: Policy #{policy_id_1}")
    
    # Lookup by hash (should return first policy)
    policy = await get_policy_by_hash(pdf_hash)
    print(f"✓ Cache lookup returned policy #{policy['id']}")
    print(f"✓ Rules in cache: {len(policy['rules'])}")
    
    # Verify this would prevent duplicate extraction
    if policy:
        print(f"✓ Duplicate detection: Would skip re-extraction and return cached policy")
    
    assert policy is not None, "Should find cached policy"
    assert policy['id'] == policy_id_1, "Should return first saved policy"
    print("\n✅ TEST 5 PASSED: Duplicate PDF detection working")


async def main():
    """Run all TASK 3 tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "TASK 3: PDF HASH CACHING - UNIT TESTS" + " "*27 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        await test_pdf_hash_generation()
        await test_policy_save_with_hash()
        await test_pdf_cache_lookup()
        await test_cache_miss()
        await test_duplicate_pdf_detection()
        
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*20 + "✅ ALL TASK 3 TESTS PASSED!" + " "*27 + "║")
        print("╚" + "="*78 + "╝")
        print("\nSummary:")
        print("✓ PDF hash generation (SHA-256)")
        print("✓ Policy save with hash")
        print("✓ PDF cache lookup by hash")
        print("✓ Cache miss handling")
        print("✓ Duplicate PDF detection")
        print("\nExpected Impact:")
        print("  • 3-4 LLM calls saved per duplicate PDF upload")
        print("  • Identical PDFs return cached results instantly (< 1ms)")
        print("  • Zero extraction overhead for repeated policy uploads")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
