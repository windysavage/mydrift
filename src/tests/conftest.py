from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from database.mongodb.base import init_mongodb_cols
from database.qdrant.base import init_qdrant_cols
from database.qdrant.client import async_qdrant_client
from database.qdrant.rag_vec_store import RAGVecStore
from utils import generate_message_chunk_id


@pytest_asyncio.fixture(scope='class')
async def setup_qdrant_env() -> AsyncGenerator:
    await init_qdrant_cols()
    yield
    # await clear_qdrant_cols()


@pytest.fixture(scope='class')
async def setup_mongodb_env() -> AsyncGenerator:
    await init_mongodb_cols()
    yield
    # await clear_mongodb()


@pytest_asyncio.fixture(scope='class')
async def upsert_mock_chunks() -> list[dict]:
    MOCK_CHUNKS = [
        {
            'chunk_id': generate_message_chunk_id(
                start_ts=0, end_ts=100, senders=['MOCK_SENDER_1', 'MOCK_SENDER_2']
            ),
            'embedding': [0.1] * 768,
            'source': 'message',
        }
    ]
    async with async_qdrant_client() as client:
        async for _ in RAGVecStore.iter_upsert_points(
            client=client,
            batched_iter_points=RAGVecStore.prepare_iter_points(MOCK_CHUNKS),
        ):
            pass
    return MOCK_CHUNKS
