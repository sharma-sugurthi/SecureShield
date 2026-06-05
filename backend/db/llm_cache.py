"""
SQLite-backed LLM Response Cache

Stores LLM responses by hash of (model, prompt) to avoid redundant API calls.
- Deterministic extraction results never expire (e.g., policy rules)
- Chat responses can expire after TTL (optional, default: no expiry)
- Uses SHA-256 hashing for cache keys
- Async-first with aiosqlite

Schema: id | model_provider | prompt_hash | response_text | ttl_expires_at | created_at
"""

import aiosqlite
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_llm_cache():
    """Create llm_cache table if it doesn't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_provider TEXT NOT NULL,
                prompt_hash TEXT NOT NULL UNIQUE,
                response_text TEXT NOT NULL,
                ttl_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for faster lookups
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_cache_model_hash 
            ON llm_cache(model_provider, prompt_hash)
        """)
        
        await db.commit()
        logger.info("[LLMCache] Table initialized")


def _hash_prompt(model: str, prompt_dict: dict) -> str:
    """
    Generate a stable SHA-256 hash for (model + prompt payload).
    
    Ignores volatile fields like temperature/max_tokens if desired for broader cache hits.
    For now: include all fields for strict matching.
    
    Args:
        model: LLM model name
        prompt_dict: Request payload (messages, temperature, max_tokens, etc.)
    
    Returns:
        SHA-256 hex digest
    """
    # Normalize the payload: sort keys and use consistent JSON format
    payload_json = json.dumps(
        {"model": model, **prompt_dict},
        sort_keys=True,
        separators=(",", ":"),
        default=str  # Handle any non-JSON-serializable types
    )
    return hashlib.sha256(payload_json.encode()).hexdigest()


async def get_cached(
    model: str,
    prompt_dict: dict,
) -> Optional[str]:
    """
    Retrieve a cached LLM response if it exists and hasn't expired.
    
    Args:
        model: LLM model name (e.g., "llama-3.3-70b-versatile")
        prompt_dict: Full request payload (messages, temperature, max_tokens, etc.)
    
    Returns:
        Response text if found and valid, None otherwise
    """
    prompt_hash = _hash_prompt(model, prompt_dict)
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT response_text, ttl_expires_at FROM llm_cache
                WHERE model_provider = ? AND prompt_hash = ?
                LIMIT 1
                """,
                (model, prompt_hash)
            )
            row = await cursor.fetchone()
            
            if row is None:
                return None
            
            response = dict(row)
            
            # Check if expired
            if response["ttl_expires_at"]:
                expires_at = datetime.fromisoformat(response["ttl_expires_at"])
                if datetime.utcnow() > expires_at:
                    logger.debug(f"[LLMCache] Cache entry expired for {model} → {prompt_hash[:8]}...")
                    return None
            
            logger.info(f"[LLMCache] ⚡ Cache HIT for {model} → {prompt_hash[:8]}...")
            return response["response_text"]
    
    except Exception as e:
        logger.warning(f"[LLMCache] Error reading cache: {e}")
        return None


async def set_cached(
    model: str,
    prompt_dict: dict,
    response_text: str,
    ttl_days: Optional[int] = None,
) -> bool:
    """
    Store an LLM response in the cache.
    
    Args:
        model: LLM model name
        prompt_dict: Full request payload
        response_text: The LLM response to cache
        ttl_days: Optional TTL in days. If None, never expires (for deterministic results).
                 Common values: 7 (weekly refresh for chat), None (permanent for policy extraction)
    
    Returns:
        True if saved successfully, False otherwise
    """
    prompt_hash = _hash_prompt(model, prompt_dict)
    expires_at = None
    
    if ttl_days:
        expires_at = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat()
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Use REPLACE to handle duplicate keys (re-cache on re-request)
            await db.execute(
                """
                REPLACE INTO llm_cache (model_provider, prompt_hash, response_text, ttl_expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (model, prompt_hash, response_text, expires_at)
            )
            await db.commit()
            
            ttl_str = f" (expires in {ttl_days} days)" if ttl_days else " (permanent)"
            logger.info(f"[LLMCache] Cached response for {model} → {prompt_hash[:8]}...{ttl_str}")
            return True
    
    except Exception as e:
        logger.warning(f"[LLMCache] Error writing cache: {e}")
        return False


async def clear_expired():
    """Remove all expired cache entries (run periodically in background)."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            result = await db.execute(
                """
                DELETE FROM llm_cache
                WHERE ttl_expires_at IS NOT NULL AND ttl_expires_at < ?
                """,
                (datetime.utcnow().isoformat(),)
            )
            await db.commit()
            logger.info(f"[LLMCache] Cleared {result.rowcount} expired entries")
    except Exception as e:
        logger.warning(f"[LLMCache] Error clearing expired entries: {e}")


async def get_cache_stats() -> dict:
    """Get cache statistics (total entries, expired, by model)."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Total entries
            cursor = await db.execute("SELECT COUNT(*) as count FROM llm_cache")
            total = (await cursor.fetchone())["count"]
            
            # Entries by model
            cursor = await db.execute(
                """
                SELECT model_provider, COUNT(*) as count 
                FROM llm_cache 
                GROUP BY model_provider 
                ORDER BY count DESC
                """
            )
            by_model = {row["model_provider"]: row["count"] async for row in cursor}
            
            # Expired entries (with TTL)
            cursor = await db.execute(
                """
                SELECT COUNT(*) as count FROM llm_cache
                WHERE ttl_expires_at IS NOT NULL AND ttl_expires_at < ?
                """,
                (datetime.utcnow().isoformat(),)
            )
            expired = (await cursor.fetchone())["count"]
            
            return {
                "total_entries": total,
                "by_model": by_model,
                "expired_entries": expired,
                "permanent_entries": total - expired,
            }
    except Exception as e:
        logger.warning(f"[LLMCache] Error getting stats: {e}")
        return {}
