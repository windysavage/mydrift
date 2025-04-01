from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from qdrant_client import QdrantClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient

QDRANT_HOST = 'http://qdrant:6333'


@asynccontextmanager
async def async_qdrant_client() -> AsyncGenerator[AsyncQdrantClient, None]:
    client = AsyncQdrantClient(url=QDRANT_HOST)
    try:
        yield client
    finally:
        await client.close()


@contextmanager
def qdrant_client() -> Generator[QdrantClient, None, None]:
    client = QdrantClient(url=QDRANT_HOST)
    try:
        yield client
    finally:
        client.close()
