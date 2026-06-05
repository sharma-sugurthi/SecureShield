SecureShield Database Migration Guide

Goal: Move from SQLite (development) to a production RDBMS (PostgreSQL or MySQL).

Overview
- SQLite is fine for development but single-process and limited for production.
- Recommended production choices: PostgreSQL (preferred) or MySQL (compatible).

Steps (Postgres)
1. Provision a Postgres instance (managed: Heroku, RDS, Neon, Supabase). Note connection string.
2. Install client library: `pip install psycopg2-binary` (or use `psycopg2` for production builds).
3. Update config in `backend/config.py` to include `DATABASE_URL` or `PG_DSN`.
4. Run the migration helper:

```bash
export SQLITE_DB=/absolute/path/to/dev.sqlite3
export PG_DSN="postgresql://user:pass@host:5432/dbname"
python3 scripts/migrate_sqlite_to_postgres.py
```

5. Update `backend/db/database.py` to use `asyncpg` or `SQLAlchemy` for async connections. Example:
   - For minimal changes, replace `aiosqlite` calls with `asyncpg` or `databases` package.
   - Alternatively, use SQLAlchemy 2.0 async engine.

6. Run application pointing to Postgres and validate endpoints.

Steps (MySQL)
- Replace `psycopg2` with `pymysql` or `mysqlclient` and adjust DDL types if needed.
- Use suitable migration script (not included). Consider using `alembic` for migrations.

Best Practices
- Use migrations: adopt `alembic` or `yoyo-migrations` for schema evolution.
- Use connection pooling (asyncpg has pool support) and retry/backoff policies.
- Centralize database config in `backend/config.py` and support both `DATABASE_PATH` (sqlite) and `DATABASE_URL` (postgres/mysql).
- Move rate-limiter to Redis for multi-process deployments.

Notes on SecureShield
- Current `backend/db/database.py` uses `aiosqlite`. For Postgres, implement an `asyncpg` equivalent:
  - `asyncpg.connect(dsn)`
  - Use `await conn.execute(...)` and `await conn.fetchrow(...)`
- Tests can still run against a local SQLite during CI, but run integration tests against a Postgres staging instance before deployment.

Migration Helpers
- `scripts/migrate_sqlite_to_postgres.py` — best-effort data copy using `psycopg2` (synchronous).
- For production, consider a more robust ETL to preserve IDs and timestamps.

If you want, I can:
- Implement `asyncpg`-based DB layer and switch `backend/db/database.py` to support Postgres transparently with a `DATABASE_URL` fallback.
- Add Alembic migrations and migrate existing schema.
- Add Redis-backed rate tracker for multi-process rate limiting.

Tell me which of the above you'd like me to implement next (asyncpg migration, alembic, Redis rate tracker), and I'll start TASK 5 integration work and DB migration coding.