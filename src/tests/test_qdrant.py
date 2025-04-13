import pytest

from database.qdrant.client import async_qdrant_client
from database.qdrant.rag_vec_store import RAGVecStore


@pytest.mark.usefixtures('setup_qdrant_env')
class TestQdrant:
    @pytest.mark.asyncio
    async def test_upsert(self, upsert_mock_chunks: list[dict]) -> None:
        assert len(upsert_mock_chunks) == 1

    @pytest.mark.asyncio
    async def test_search(self, upsert_mock_chunks: list[dict]) -> None:
        async with async_qdrant_client() as client:
            chunk_id = upsert_mock_chunks[0]['chunk_id']
            async with async_qdrant_client() as client:
                results = await RAGVecStore.search(
                    client=client,
                    query_vector=[0.1] * 768,
                    limit=1,
                )
            assert chunk_id == results[0].id.replace('-', '')
