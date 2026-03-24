"""
SQLite database operations for SecureShield.
Stores ingested policy rules and eligibility check history.
"""

import aiosqlite
import json
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insurer TEXT NOT NULL,
                plan_name TEXT NOT NULL,
                sum_insured REAL NOT NULL,
                policy_type TEXT DEFAULT 'individual',
                rules_json TEXT NOT NULL,
                raw_text_hash TEXT,
                is_reviewed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS eligibility_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                case_json TEXT NOT NULL,
                verdict_json TEXT NOT NULL,
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (policy_id) REFERENCES policies (id)
            )
        """)

        await db.commit()
        logger.info("[Database] Tables initialized")


async def save_policy(insurer: str, plan_name: str, sum_insured: float,
                      policy_type: str, rules: list[dict], raw_text_hash: str) -> int:
    """Save an ingested policy and return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO policies (insurer, plan_name, sum_insured, policy_type, rules_json, raw_text_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (insurer, plan_name, sum_insured, policy_type, json.dumps(rules), raw_text_hash)
        )
        await db.commit()
        policy_id = cursor.lastrowid
        logger.info(f"[Database] Saved policy #{policy_id}: {insurer} - {plan_name}")
        return policy_id


async def get_policy(policy_id: int) -> dict | None:
    """Retrieve a policy by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM policies WHERE id = ?", (policy_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        policy = dict(row)
        policy["rules"] = json.loads(policy["rules_json"])
        return policy


async def get_all_policies() -> list[dict]:
    """Retrieve all ingested policies (without full rules for listing)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, insurer, plan_name, sum_insured, policy_type, is_reviewed, created_at FROM policies ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_eligibility_check(policy_id: int, case_json: str,
                                  verdict_json: str, explanation: str) -> int:
    """Save an eligibility check result."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO eligibility_checks (policy_id, case_json, verdict_json, explanation)
               VALUES (?, ?, ?, ?)""",
            (policy_id, case_json, verdict_json, explanation)
        )
        await db.commit()
        return cursor.lastrowid


async def get_check_history(limit: int = 20) -> list[dict]:
    """Retrieve recent eligibility check history."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT ec.id, ec.policy_id, p.insurer, p.plan_name, 
                      ec.verdict_json, ec.created_at
               FROM eligibility_checks ec
               JOIN policies p ON ec.policy_id = p.id
               ORDER BY ec.created_at DESC
               LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["verdict"] = json.loads(d["verdict_json"])
            del d["verdict_json"]
            results.append(d)
        return results
