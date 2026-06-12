import asyncio
from utils.mailer import send_welcome_email

async def main():
    await send_welcome_email("help.secureshield@gmail.com")

if __name__ == "__main__":
    asyncio.run(main())
