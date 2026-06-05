"""
Rate Tracker — lightweight in-memory sliding window rate limiter per provider.

Features:
- Configurable per-provider limits (requests per minute) for free-tier providers.
- Sliding window using time-bucketed counters for efficiency.
- Async-safe with per-provider locks.
- Exposes:
  - `record_call(provider_name)` — record an API call timestamp
  - `can_call(provider_name)` — whether a call is allowed now
  - `get_available_providers()` — returns providers sorted by availability (most free capacity first)
  - `get_status()` — debug snapshot of usage counts and limits

This is intended as a lightweight in-memory tracker suitable for single-process deployments.
For multi-process / multi-host production, migrate to Redis-based counters.
"""

import time
import asyncio
from collections import deque
import os
from importlib import import_module
from typing import Dict, Deque, Tuple, List
import logging

logger = logging.getLogger(__name__)

# Free-tier limits (RPM) — adjust as necessary
DEFAULT_LIMITS = {
    "cerebras": 30,
    "groq": 30,
    "google": 15,
    "together": 10,
    "openrouter": 5,
    "xai": 20,
}

# Threshold at which providers are considered "near capacity" (e.g., 85%)
NEAR_CAPACITY_RATIO = 0.85

# Window length in seconds (60 seconds for per-minute limits)
WINDOW_SECONDS = 60


class ProviderWindow:
    def __init__(self, limit: int):
        self.limit = limit
        self.timestamps: Deque[float] = deque()
        self.lock = asyncio.Lock()

    def _prune(self, now: float):
        # remove timestamps older than WINDOW_SECONDS
        while self.timestamps and (now - self.timestamps[0]) > WINDOW_SECONDS:
            self.timestamps.popleft()

    async def record(self) -> None:
        now = time.time()
        async with self.lock:
            self._prune(now)
            self.timestamps.append(now)

    async def count(self) -> int:
        now = time.time()
        async with self.lock:
            self._prune(now)
            return len(self.timestamps)

    async def available_capacity(self) -> int:
        cnt = await self.count()
        return max(0, self.limit - cnt)

    async def is_near_capacity(self) -> bool:
        cnt = await self.count()
        return cnt >= int(self.limit * NEAR_CAPACITY_RATIO)

    async def is_exhausted(self) -> bool:
        cnt = await self.count()
        return cnt >= self.limit


class RateTracker:
    def __init__(self, limits: Dict[str, int] = None):
        self.limits = limits or DEFAULT_LIMITS.copy()
        self.windows: Dict[str, ProviderWindow] = {
            name: ProviderWindow(limit) for name, limit in self.limits.items()
        }

    def _ensure_provider(self, provider: str):
        if provider not in self.windows:
            # default conservative limit
            self.limits[provider] = 10
            self.windows[provider] = ProviderWindow(10)

    async def record_call(self, provider: str) -> None:
        """Record a single API call for provider."""
        self._ensure_provider(provider)
        await self.windows[provider].record()

    async def can_call(self, provider: str) -> bool:
        """Return True if call is allowed (limit not exhausted)."""
        self._ensure_provider(provider)
        return not await self.windows[provider].is_exhausted()

    async def is_near_capacity(self, provider: str) -> bool:
        self._ensure_provider(provider)
        return await self.windows[provider].is_near_capacity()

    async def get_available_providers(self) -> List[Tuple[str, int]]:
        """Return list of (provider, available_capacity) sorted desc by capacity."""
        snapshot = []
        for name, window in self.windows.items():
            cap = await window.available_capacity()
            snapshot.append((name, cap))
        snapshot.sort(key=lambda x: x[1], reverse=True)
        return snapshot

    async def get_status(self) -> Dict[str, Dict]:
        """Return debugging status for all providers."""
        status = {}
        for name, window in self.windows.items():
            cnt = await window.count()
            status[name] = {
                "limit": window.limit,
                "count_last_min": cnt,
                "available": max(0, window.limit - cnt),
                "near_capacity": cnt >= int(window.limit * NEAR_CAPACITY_RATIO),
                "exhausted": cnt >= window.limit,
            }
        return status


# Singleton instance
rate_tracker = RateTracker()


# Convenience async wrappers
async def record_call(provider: str) -> None:
    await rate_tracker.record_call(provider)


async def can_call(provider: str) -> bool:
    return await rate_tracker.can_call(provider)


async def get_available_providers() -> List[Tuple[str, int]]:
    return await rate_tracker.get_available_providers()


async def get_status() -> Dict[str, Dict]:
    return await rate_tracker.get_status()


# If REDIS_URL is provided, prefer a Redis-backed tracker for multi-process safety
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    try:
        from .redis_rate_tracker import redis_tracker as _redis_tracker

        if _redis_tracker:
            # Delegate functions to redis tracker
            async def record_call(provider: str) -> None:
                await _redis_tracker.record_call(provider)

            async def can_call(provider: str) -> bool:
                return await _redis_tracker.can_call(provider)

            async def get_available_providers() -> List[Tuple[str, int]]:
                return await _redis_tracker.get_available_providers()

            async def get_status() -> Dict[str, Dict]:
                return await _redis_tracker.get_status()

            rate_tracker = _redis_tracker
            logger.info("[RateTracker] Using Redis-backed rate tracker")
    except Exception:
        logger.exception("Failed to initialize Redis rate tracker; falling back to in-memory")
