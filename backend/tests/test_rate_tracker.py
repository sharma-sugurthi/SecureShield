"""
Unit tests for backend/utils/rate_tracker.py
"""
import asyncio
import time
from utils.rate_tracker import rate_tracker, record_call, can_call, get_available_providers, get_status


async def test_rate_record_and_limits():
    print("\n[TEST] Rate Tracker: record and limit enforcement")
    # Use a test provider with small limit
    provider = "test_provider"
    rate_tracker.limits[provider] = 5
    rate_tracker.windows[provider] = type(rate_tracker.windows.get("groq"))(5)

    # Initially should be callable
    allowed = await can_call(provider)
    print(f"✓ Initially can_call: {allowed}")
    assert allowed

    # Record 5 calls
    for i in range(5):
        await record_call(provider)
    
    allowed_after = await can_call(provider)
    print(f"✓ After {5} calls can_call: {allowed_after}")
    assert not allowed_after, "Provider should be exhausted after reaching limit"

    # Get status
    status = await get_status()
    print(f"✓ Status for {provider}: {status[provider]}")
    assert status[provider]["count_last_min"] == 5

    # Sleep past window to allow pruning
    print("Waiting for window to expire (2s)...")
    time.sleep(2)
    # Manually prune by calling count()
    cnt = await rate_tracker.windows[provider].count()
    print(f"✓ Count after short wait: {cnt} (may still be >0)")

    print("\n✅ Rate Tracker basic enforcement test done")
    return True


async def test_available_providers_ordering():
    print("\n[TEST] Rate Tracker: provider ordering by available capacity")
    # Reset windows for predictable state
    for name in ["google", "groq", "cerebras", "together", "openrouter"]:
        rate_tracker.windows[name] = type(rate_tracker.windows.get(name))(rate_tracker.limits[name])

    # Simulate some calls to google and groq
    for _ in range(10):
        await record_call("google")
    for _ in range(2):
        await record_call("groq")

    avail = await get_available_providers()
    print("✓ Availability snapshot:")
    for name, cap in avail:
        print(f"  - {name}: {cap}")

    # Ensure groq has more capacity than google now
    cap_map = {n: c for n, c in avail}
    assert cap_map["groq"] > cap_map["google"]

    print("\n✅ Provider ordering test done")
    return True


async def main():
    await test_rate_record_and_limits()
    await test_available_providers_ordering()


if __name__ == "__main__":
    asyncio.run(main())
