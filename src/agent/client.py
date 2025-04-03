from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from ollama import AsyncClient

from settings import settings


@asynccontextmanager
async def async_ollama_client() -> AsyncGenerator[AsyncClient, None]:
    client = AsyncClient(host=settings.OLLAMA_HOST)
    try:
        yield client
    finally:
        await client._client.aclose()
