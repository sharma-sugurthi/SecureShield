"""
Redis-backed rate tracker for multi-process safe rate limiting.

Implements per-provider counters using Redis keys with minute window.
Key format: rate:{provider}:{window_ts}
"""
import os
import time
import logging
from typing import Dict, List, Tuple

import redis.asyncio as redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
DEFAULT_LIMITS = {
    "cerebras": 30,
    "groq": 30,
    "google": 15,
    "openrouter": 5,
    "xai": 20,
}

NEAR_CAPACITY_RATIO = 0.85
WINDOW_SECONDS = 60


class RedisRateTracker:
    def __init__(self, url: str | None = None, limits: Dict[str, int] = None):
        self.url = url or REDIS_URL
        if not self.url:
            raise RuntimeError("REDIS_URL not set")
        self.client = redis.from_url(self.url, encoding="utf-8", decode_responses=True)
        self.limits = limits or DEFAULT_LIMITS.copy()

    def _key(self, provider: str) -> str:
        window = int(time.time() // WINDOW_SECONDS)
        return f"rate:{provider}:{window}"

    async def record_call(self, provider: str) -> None:
        key = self._key(provider)
        pipe = self.client.pipeline()
        pipe.incr(key, amount=1)
        pipe.expire(key, WINDOW_SECONDS * 2)
        await pipe.execute()

    async def count(self, provider: str) -> int:
        key = self._key(provider)
        val = await self.client.get(key)
        return int(val or 0)

    async def can_call(self, provider: str) -> bool:
        limit = self.limits.get(provider, 10)
        cnt = await self.count(provider)
        return cnt < limit

    async def is_near_capacity(self, provider: str) -> bool:
        limit = self.limits.get(provider, 10)
        cnt = await self.count(provider)
        return cnt >= int(limit * NEAR_CAPACITY_RATIO)

    async def get_available_providers(self) -> List[Tuple[str, int]]:
        snapshot = []
        for name, limit in self.limits.items():
            cnt = await self.count(name)
            snapshot.append((name, max(0, limit - cnt)))
        snapshot.sort(key=lambda x: x[1], reverse=True)
        return snapshot

    async def get_status(self) -> Dict[str, Dict]:
        status = {}
        for name, limit in self.limits.items():
            cnt = await self.count(name)
            status[name] = {
                "limit": limit,
                "count_last_min": cnt,
                "available": max(0, limit - cnt),
                "near_capacity": cnt >= int(limit * NEAR_CAPACITY_RATIO),
                "exhausted": cnt >= limit,
            }
        return status


redis_tracker: RedisRateTracker | None = None
try:
    if REDIS_URL:
        redis_tracker = RedisRateTracker()
except Exception:
    logger.exception("Failed to initialize RedisRateTracker")


__all__ = ["RedisRateTracker", "redis_tracker"]
