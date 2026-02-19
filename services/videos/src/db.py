from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB]


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return db
