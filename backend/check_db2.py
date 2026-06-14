import asyncio
from db.database import get_all_policies

async def main():
    print("Testing get_all_policies(user_id='api_client'):")
    pols = await get_all_policies(user_id='api_client')
    print("Results:")
    for p in pols:
        print(p['id'], p['plan_name'], p['user_id'] if 'user_id' in p else 'N/A')

asyncio.run(main())
