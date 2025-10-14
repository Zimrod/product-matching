from telethon import TelegramClient
from config import Config

api_id = int(Config.API_ID)
api_hash = Config.API_HASH

client = TelegramClient("telegram_session", api_id, api_hash)

async def main():
    await client.start()
    print("✅ Authentication successful!")
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username})")
    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())