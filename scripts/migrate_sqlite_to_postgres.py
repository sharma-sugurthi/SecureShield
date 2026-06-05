"""
Simple migration helper: SQLite -> PostgreSQL

Usage:
  export SQLITE_DB=/path/to/sqlite.db
  export PG_DSN="postgresql://user:pass@host:5432/dbname"
  python3 scripts/migrate_sqlite_to_postgres.py

Notes:
- Installs required: `psycopg2-binary` (or `psycopg2`).
- This script performs a best-effort table creation and data copy for the schema used by SecureShield.
- Review and test on a staging database before production.
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

SQLITE_DB = os.environ.get("SQLITE_DB", "backend/secure_shield.db")
PG_DSN = os.environ.get("PG_DSN")

if not PG_DSN:
    print("ERROR: PG_DSN environment variable not set. Example: postgresql://user:pass@host:5432/dbname")
    raise SystemExit(1)

# Define table creation DDL for Postgres (based on backend/db/database.py schema)
CREATE_POLICIES = """
CREATE TABLE IF NOT EXISTS policies (
    id SERIAL PRIMARY KEY,
    insurer TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    sum_insured REAL NOT NULL,
    policy_type TEXT DEFAULT 'individual',
    rules_json TEXT NOT NULL,
    raw_text_hash TEXT UNIQUE,
    is_reviewed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_policies_hash ON policies(raw_text_hash);
"""

CREATE_ELIGIBILITY = """
CREATE TABLE IF NOT EXISTS eligibility_checks (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER NOT NULL REFERENCES policies(id),
    case_json TEXT NOT NULL,
    verdict_json TEXT NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def read_sqlite(sqlite_path: str):
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Read policies
    cur.execute("SELECT * FROM policies")
    policies = [dict(row) for row in cur.fetchall()]

    # Read eligibility_checks
    cur.execute("SELECT * FROM eligibility_checks")
    checks = [dict(row) for row in cur.fetchall()]

    conn.close()
    return policies, checks


def migrate(policies, checks):
    conn = psycopg2.connect(PG_DSN)
    cur = conn.cursor()

    # Create tables
    cur.execute(CREATE_POLICIES)
    cur.execute(CREATE_ELIGIBILITY)
    conn.commit()

    # Insert policies
    if policies:
        rows = []
        for p in policies:
            rows.append((p['insurer'], p['plan_name'], p['sum_insured'], p.get('policy_type', 'individual'), p['rules_json'], p.get('raw_text_hash')))
        execute_values(cur,
                       "INSERT INTO policies (insurer, plan_name, sum_insured, policy_type, rules_json, raw_text_hash) VALUES %s RETURNING id",
                       rows)
        conn.commit()
        print(f"Inserted {len(rows)} policies")

    # Insert eligibility checks
    if checks:
        rows = []
        for c in checks:
            rows.append((c['policy_id'], c['case_json'], c['verdict_json'], c.get('explanation')))
        execute_values(cur,
                       "INSERT INTO eligibility_checks (policy_id, case_json, verdict_json, explanation) VALUES %s",
                       rows)
        conn.commit()
        print(f"Inserted {len(rows)} eligibility checks")

    cur.close()
    conn.close()


if __name__ == '__main__':
    print("Reading from SQLite...", SQLITE_DB)
    policies, checks = read_sqlite(SQLITE_DB)
    print(f"Found {len(policies)} policies and {len(checks)} checks")
    print("Migrating to Postgres...")
    migrate(policies, checks)
    print("Migration complete. Verify your Postgres database.")
