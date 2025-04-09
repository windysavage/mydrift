from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from ollama import AsyncClient
from openai import AsyncOpenAI

from settings import get_settings


@asynccontextmanager
async def async_ollama_client() -> AsyncGenerator[AsyncClient, None]:
    client = AsyncClient(host=get_settings().OLLAMA_HOST)
    try:
        yield client
    finally:
        await client._client.aclose()


@asynccontextmanager
async def async_openai_client(
    api_key: str | None = None,
) -> AsyncGenerator[AsyncOpenAI, None]:
    client = AsyncOpenAI(api_key=api_key or get_settings().OPENAI_API_KEY)
    try:
        yield client
    finally:
        await client.close()
