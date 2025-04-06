from collections.abc import Iterable, Sequence

from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.conversions.common_types import ScoredPoint
from qdrant_client.http import models
from qdrant_client.http.models import (
    FieldCondition,
    HnswConfigDiff,
    MatchAny,
    MatchValue,
    NamedVector,
)

from database.qdrant.client import async_qdrant_client


async def init_qdrant_cols() -> None:
    from database.qdrant.chat_vec import ChatVec

    all_cols = [ChatVec]
    async with async_qdrant_client() as client:
        for col in all_cols:
            await col.create_collection(client=client)


class BaseVecCol:
    def __init_subclass__(cls, **kwargs: dict) -> None:
        super().__init_subclass__(**kwargs)
        required_attrs = [
            'COLLECTION_BASE_NAME',
            'COLLECTION_VERSION_NAME',
            'VECTOR_CONFIG',
            'HNSW_CONFIG',
        ]
        for attr in required_attrs:
            if getattr(cls, attr, None) is None:
                raise TypeError(f'Class `{cls.__name__}` must define `{attr}`')

        cls.check_cls_config()

    @classmethod
    def check_cls_config(cls) -> None:
        assert isinstance(cls.COLLECTION_BASE_NAME, str)
        assert isinstance(cls.COLLECTION_VERSION_NAME, str)
        assert isinstance(cls.VECTOR_CONFIG, dict)
        assert isinstance(cls.HNSW_CONFIG, HnswConfigDiff)

    @classmethod
    def get_full_collection_name(cls) -> str:
        return f'{cls.COLLECTION_BASE_NAME}-{cls.COLLECTION_VERSION_NAME}'

    @classmethod
    async def create_collection(cls, client: AsyncQdrantClient) -> None:
        full_collection_name = cls.get_full_collection_name()
        if not await client.collection_exists(collection_name=full_collection_name):
            try:
                await client.create_collection(
                    collection_name=full_collection_name,
                    vectors_config=cls.VECTOR_CONFIG,
                    hnsw_config=cls.HNSW_CONFIG,
                )
            except Exception as e:
                raise RuntimeError(f'Failed to create "{full_collection_name}"') from e

    @classmethod
    async def iter_upsert_points(
        cls, client: AsyncQdrantClient, batched_iter_points: Iterable
    ) -> None:
        for batched_point in batched_iter_points:
            await client.upsert(
                collection_name=cls.get_full_collection_name(), points=batched_point
            )

    @classmethod
    async def search(
        cls,
        client: AsyncQdrantClient,
        query_vector: Sequence[float],
        threshold: float = 0.0,
        limit: int = 10,
        offset: int = 0,
        with_vectors: bool = False,
        with_payload: list[str] | bool = True,
        include_filter_map: dict | None = None,
        exclude_filter_map: dict | None = None,
    ) -> list[ScoredPoint]:
        query_filter = None
        query_filter = cls._build_filter_conditions(
            include_filter_map=include_filter_map, exclude_filter_map=exclude_filter_map
        )
        return await client.search(
            collection_name=cls.get_full_collection_name(),
            query_vector=NamedVector(name='default', vector=query_vector),
            limit=limit,
            offset=offset,
            query_filter=query_filter,
            score_threshold=threshold,
            with_vectors=with_vectors,
            with_payload=with_payload,
        )

    @classmethod
    def _build_field_condition(cls, key: str, value: object) -> FieldCondition:
        if isinstance(value, Iterable) and not isinstance(value, str | bytes | dict):
            match = MatchAny(any=value)
        else:
            match = MatchValue(value=value)

        return FieldCondition(key=key, match=match)

    @classmethod
    def _build_filter_conditions(
        cls,
        include_filter_map: dict | None = None,
        exclude_filter_map: dict | None = None,
    ) -> models.Filter:
        must = (
            [
                cls._build_field_condition(include_key, include_value)
                for include_key, include_value in include_filter_map.items()
            ]
            if include_filter_map
            else None
        )
        must_not = (
            [
                cls._build_field_condition(exclude_key, exclude_value)
                for exclude_key, exclude_value in exclude_filter_map.items()
            ]
            if exclude_filter_map
            else None
        )

        return models.Filter(must=must, must_not=must_not)
