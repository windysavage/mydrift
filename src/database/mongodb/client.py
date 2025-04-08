from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient

from settings import settings


@asynccontextmanager
async def async_mongodb_client(
    host: str = None,
) -> AsyncGenerator[AsyncIOMotorClient, None]:
    client = AsyncIOMotorClient(host or settings.MONGODB_HOST)
    try:
        yield client
    finally:
        client.close()
