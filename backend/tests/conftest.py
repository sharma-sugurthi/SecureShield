"""
Shared test fixtures for SecureShield backend tests.
Ensures database tables are created before any test that needs them.
"""

import sys
import os
import asyncio
import pytest

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    """Initialize database tables once before all tests run."""
    from db.database import init_db
    from db.llm_cache import init_llm_cache

    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.run_until_complete(init_llm_cache())
    loop.close()
