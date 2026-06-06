"""
SQLAlchemy ORM-backed LLM Response Cache

Stores LLM responses by hash of (model, prompt) to avoid redundant API calls.
- Deterministic extraction results never expire (e.g., policy rules)
- Chat responses can expire after TTL (optional, default: no expiry)
- Uses SHA-256 hashing for cache keys
- Database-agnostic via SQLAlchemy ORM (works with SQLite, PostgreSQL, MySQL)

Schema: id | model_provider | prompt_hash | response_text | ttl_expires_at | created_at
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Text, DateTime, func, select, delete
from db.database import Base, AsyncSessionLocal, engine

logger = logging.getLogger(__name__)


class LLMCacheEntry(Base):
    """SQLAlchemy ORM model for LLM response cache entries."""
    __tablename__ = "llm_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    ttl_expires_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def init_llm_cache():
    """Create llm_cache table if it doesn't exist (via SQLAlchemy ORM)."""
    async with engine.begin() as conn:
        # Only create the llm_cache table — other tables are handled by database.init_db()
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[LLMCache] ORM table initialized")


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
        async with AsyncSessionLocal() as session:
            stmt = (
                select(LLMCacheEntry)
                .where(
                    LLMCacheEntry.model_provider == model,
                    LLMCacheEntry.prompt_hash == prompt_hash,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()

            if entry is None:
                return None

            # Check if expired
            if entry.ttl_expires_at:
                if datetime.utcnow() > entry.ttl_expires_at:
                    logger.debug(f"[LLMCache] Cache entry expired for {model} → {prompt_hash[:8]}...")
                    return None

            logger.info(f"[LLMCache] ⚡ Cache HIT for {model} → {prompt_hash[:8]}...")
            return entry.response_text

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
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)

    try:
        async with AsyncSessionLocal() as session:
            # Check if entry already exists
            stmt = select(LLMCacheEntry).where(LLMCacheEntry.prompt_hash == prompt_hash)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing entry
                existing.response_text = response_text
                existing.ttl_expires_at = expires_at
                existing.model_provider = model
            else:
                # Insert new entry
                entry = LLMCacheEntry(
                    model_provider=model,
                    prompt_hash=prompt_hash,
                    response_text=response_text,
                    ttl_expires_at=expires_at,
                )
                session.add(entry)

            await session.commit()

            ttl_str = f" (expires in {ttl_days} days)" if ttl_days else " (permanent)"
            logger.info(f"[LLMCache] Cached response for {model} → {prompt_hash[:8]}...{ttl_str}")
            return True

    except Exception as e:
        logger.warning(f"[LLMCache] Error writing cache: {e}")
        return False


async def clear_expired():
    """Remove all expired cache entries (run periodically in background)."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = delete(LLMCacheEntry).where(
                LLMCacheEntry.ttl_expires_at.isnot(None),
                LLMCacheEntry.ttl_expires_at < datetime.utcnow(),
            )
            result = await session.execute(stmt)
            await session.commit()
            logger.info(f"[LLMCache] Cleared {result.rowcount} expired entries")
    except Exception as e:
        logger.warning(f"[LLMCache] Error clearing expired entries: {e}")


async def get_cache_stats() -> dict:
    """Get cache statistics (total entries, expired, by model)."""
    try:
        async with AsyncSessionLocal() as session:
            # Total entries
            from sqlalchemy import func as sa_func
            stmt = select(sa_func.count(LLMCacheEntry.id))
            result = await session.execute(stmt)
            total = result.scalar() or 0

            # Entries by model
            stmt = (
                select(LLMCacheEntry.model_provider, sa_func.count(LLMCacheEntry.id))
                .group_by(LLMCacheEntry.model_provider)
                .order_by(sa_func.count(LLMCacheEntry.id).desc())
            )
            result = await session.execute(stmt)
            by_model = {row[0]: row[1] for row in result.fetchall()}

            # Expired entries
            stmt = select(sa_func.count(LLMCacheEntry.id)).where(
                LLMCacheEntry.ttl_expires_at.isnot(None),
                LLMCacheEntry.ttl_expires_at < datetime.utcnow(),
            )
            result = await session.execute(stmt)
            expired = result.scalar() or 0

            return {
                "total_entries": total,
                "by_model": by_model,
                "expired_entries": expired,
                "permanent_entries": total - expired,
            }
    except Exception as e:
        logger.warning(f"[LLMCache] Error getting stats: {e}")
        return {}
