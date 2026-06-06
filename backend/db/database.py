"""
Async SQLAlchemy ORM database layer for SecureShield.

Supports both SQLite (development) and PostgreSQL (production) via SQLAlchemy
`DATABASE_URL` environment variable. Falls back to the previous `DATABASE_PATH`.

This module exposes the same async helper functions used across the codebase:
- init_db()
- save_policy(...)
- get_policy(policy_id)
- get_policy_by_hash(pdf_hash)
- get_all_policies()
- save_eligibility_check(...)
- get_check_history(limit)

It uses SQLAlchemy 2.0 async ORM so future migrations with Alembic are straightforward.
"""

import os
import json
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, Text, DateTime, func, select
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

# Database URL: prefer DATABASE_URL env var, otherwise use sqlite file path
# For production, set DATABASE_URL to a PostgreSQL/MySQL connection string:
#   DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
#   DATABASE_URL=mysql+aiomysql://user:pass@host/dbname
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use aiosqlite driver for SQLAlchemy async (development default)
    sqlite_path = os.path.join(os.path.dirname(__file__), "secureshield_new.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{sqlite_path}"

# Async engine and session
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    insurer: Mapped[str] = mapped_column(String, nullable=False)
    plan_name: Mapped[str] = mapped_column(String, nullable=False)
    sum_insured: Mapped[float] = mapped_column(Float, nullable=False)
    policy_type: Mapped[str] = mapped_column(String, default="individual")
    rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text_hash: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    is_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EligibilityCheck(Base):
    __tablename__ = "eligibility_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(Integer)
    case_json: Mapped[str] = mapped_column(Text, nullable=False)
    verdict_json: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


async def init_db():
    """Create tables if they don't exist (async)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[Database] Async ORM tables initialized")


async def save_policy(insurer: str, plan_name: str, sum_insured: float,
                      policy_type: str, rules: List[dict], raw_text_hash: Optional[str]) -> int:
    """Save an ingested policy and return its ID."""
    async with AsyncSessionLocal() as session:
        policy = Policy(
            insurer=insurer,
            plan_name=plan_name,
            sum_insured=sum_insured,
            policy_type=policy_type,
            rules_json=json.dumps(rules),
            raw_text_hash=raw_text_hash,
        )
        session.add(policy)
        await session.commit()
        await session.refresh(policy)
        logger.info(f"[Database] Saved policy #{policy.id}: {insurer} - {plan_name}")
        return policy.id


async def get_policy(policy_id: int) -> Optional[dict]:
    """Retrieve a policy by ID."""
    async with AsyncSessionLocal() as session:
        policy = await session.get(Policy, policy_id)
        if not policy:
            return None
        return {
            "id": policy.id,
            "insurer": policy.insurer,
            "plan_name": policy.plan_name,
            "sum_insured": policy.sum_insured,
            "policy_type": policy.policy_type,
            "rules": json.loads(policy.rules_json),
            "raw_text_hash": policy.raw_text_hash,
            "is_reviewed": policy.is_reviewed,
            "created_at": str(policy.created_at),
        }


async def get_policy_by_hash(pdf_hash: str) -> Optional[dict]:
    """Retrieve a policy by PDF hash (cache lookup)."""
    async with AsyncSessionLocal() as session:
        stmt = select(Policy).where(Policy.raw_text_hash == pdf_hash).limit(1)
        result = await session.execute(stmt)
        policy_obj = result.scalar_one_or_none()
        if not policy_obj:
            return None
        return {
            "id": policy_obj.id,
            "insurer": policy_obj.insurer,
            "plan_name": policy_obj.plan_name,
            "sum_insured": policy_obj.sum_insured,
            "policy_type": policy_obj.policy_type,
            "rules": json.loads(policy_obj.rules_json or "[]"),
            "raw_text_hash": policy_obj.raw_text_hash,
            "is_reviewed": policy_obj.is_reviewed,
            "created_at": str(policy_obj.created_at),
        }


async def get_all_policies() -> List[dict]:
    """Retrieve all ingested policies (without full rules for listing)."""
    async with AsyncSessionLocal() as session:
        stmt = select(
            Policy.id,
            Policy.insurer,
            Policy.plan_name,
            Policy.sum_insured,
            Policy.policy_type,
            Policy.is_reviewed,
            Policy.created_at,
        ).order_by(Policy.created_at.desc())
        q = await session.execute(stmt)
        rows = q.fetchall()
        return [
            {
                "id": r.id,
                "insurer": r.insurer,
                "plan_name": r.plan_name,
                "sum_insured": r.sum_insured,
                "policy_type": r.policy_type,
                "is_reviewed": r.is_reviewed,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]


async def save_eligibility_check(policy_id: int, case_json: str,
                                  verdict_json: str, explanation: Optional[str]) -> int:
    """Save an eligibility check result."""
    async with AsyncSessionLocal() as session:
        check = EligibilityCheck(
            policy_id=policy_id,
            case_json=case_json,
            verdict_json=verdict_json,
            explanation=explanation,
        )
        session.add(check)
        await session.commit()
        await session.refresh(check)
        return check.id


async def get_check_history(limit: int = 20) -> List[dict]:
    """Retrieve recent eligibility check history."""
    async with AsyncSessionLocal() as session:
        stmt = select(
            EligibilityCheck.id,
            EligibilityCheck.policy_id,
            EligibilityCheck.case_json,
            EligibilityCheck.verdict_json,
            EligibilityCheck.explanation,
            EligibilityCheck.created_at,
        ).order_by(EligibilityCheck.created_at.desc()).limit(limit)
        q = await session.execute(stmt)
        rows = q.fetchall()
        return [
            {
                "id": r.id,
                "policy_id": r.policy_id,
                "case_json": r.case_json,
                "verdict_json": r.verdict_json,
                "explanation": r.explanation,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]


async def clear_policies_and_checks() -> None:
    """Delete all rows from `eligibility_checks` and `policies` tables.

    Useful for tests and demo reset. Uses SQLAlchemy ORM (database-agnostic).
    """
    from sqlalchemy import delete as sa_delete

    async with AsyncSessionLocal() as session:
        await session.execute(sa_delete(EligibilityCheck))
        await session.execute(sa_delete(Policy))
        await session.commit()
    logger.info("[Database] Cleared policies and eligibility_checks tables")
