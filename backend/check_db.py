import asyncio
from db.database import AsyncSessionLocal, Policy, get_all_policies
from sqlalchemy import select

async def main():
    print("\nTesting get_all_policies(user_id='ea6e1ae9-3415-4701-9ccb-0e38f19a6b88'):")
    pols = await get_all_policies(user_id='ea6e1ae9-3415-4701-9ccb-0e38f19a6b88')
    for p in pols:
        print(p['id'], p['plan_name'])

asyncio.run(main())
