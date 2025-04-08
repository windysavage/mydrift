from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from qdrant_client.async_qdrant_client import AsyncQdrantClient

from settings import settings


@asynccontextmanager
async def async_qdrant_client(
    host: str = None,
) -> AsyncGenerator[AsyncQdrantClient, None]:
    client = AsyncQdrantClient(url=host or settings.QDRANT_HOST)
    try:
        yield client
    finally:
        await client.close()
