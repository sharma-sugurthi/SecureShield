import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

async def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set")
        return

    # Replace postgres:// with postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=True)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE app_feedback ADD COLUMN other_suggestions TEXT;"))
            print("Successfully added other_suggestions column.")
        except Exception as e:
            print(f"Error (maybe it already exists?): {e}")

if __name__ == "__main__":
    asyncio.run(main())
