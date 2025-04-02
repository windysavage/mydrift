from collections.abc import Iterable, Sequence
from typing import Any

from qdrant_client import models
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.conversions.common_types import Filter, Record, ScoredPoint
from qdrant_client.http.models import HnswConfigDiff, NamedVector


class BaseVecCol:
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        required_attrs = [
            'COLLECTION_BASE_NAME',
            'COLLECTION_VERSION_NAME',
            'NUMBER_OF_SHARDS',
            'NUMBER_OF_REPLICA',
            'PAYLOAD_COLUMNS',
            'VECTOR_CONFIG',
            'HNSW_CONFIG',
            'PAYLOAD_PARTITIONS',
            'PAYLOAD_PARTITION_TYPES',
        ]
        for attr in required_attrs:
            if getattr(cls, attr, None) is None:
                raise TypeError(f'Class `{cls.__name__}` must define `{attr}`')

        cls.check_cls_config()

    @classmethod
    def check_cls_config(cls) -> None:
        assert isinstance(cls.COLLECTION_BASE_NAME, str)
        assert isinstance(cls.COLLECTION_VERSION_NAME, str)
        assert isinstance(cls.NUMBER_OF_SHARDS, int)
        assert isinstance(cls.NUMBER_OF_REPLICA, int)
        assert isinstance(cls.PAYLOAD_COLUMNS, list)
        assert isinstance(cls.VECTOR_CONFIG, dict)
        assert isinstance(cls.HNSW_CONFIG, HnswConfigDiff)
        assert isinstance(cls.PAYLOAD_PARTITIONS, list)
        assert isinstance(cls.PAYLOAD_PARTITION_TYPES, list)

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
                    shard_number=cls.NUMBER_OF_SHARDS,
                    replication_factor=cls.NUMBER_OF_REPLICA,
                    hnsw_config=cls.HNSW_CONFIG,
                )
            except Exception as e:
                raise RuntimeError(f'Failed to create collection "{full_collection_name}"') from e

    @classmethod
    async def iter_upsert_points(cls, client: AsyncQdrantClient, points: Iterable) -> None:
        for batched_point in points:
            await client.upsert(
                collection_name=cls.get_full_collection_name(), points=batched_point
            )

    @classmethod
    async def create_payload_partition(cls, client: AsyncQdrantClient) -> None:
        full_collection_name = cls.get_full_collection_name()
        try:
            for partition, partition_type in zip(
                cls.PAYLOAD_PARTITIONS, cls.PAYLOAD_PARTITION_TYPES, strict=True
            ):
                await client.create_payload_index(
                    collection_name=full_collection_name,
                    field_name=partition,
                    field_schema=partition_type,
                )
        except Exception as e:
            raise RuntimeError(f'Failed to partition collection "{full_collection_name}"') from e

    @classmethod
    async def search(
        cls,
        client: AsyncQdrantClient,
        query_vector: Sequence[float],
        threshold: float = 0.0,
        limit: int = 30,
        offset: int = 0,
        with_vectors: bool = False,
        with_payload: list[str] | bool = True,
        include_filter_map: dict | None = None,
        exclude_filter_map: dict | None = None,
    ) -> list[ScoredPoint]:
        query_filter = None
        query_filter = cls._get_filter_condition(
            include_filter_map=include_filter_map, exclude_filter_map=exclude_filter_map
        )

        return await cls._search(
            client=client,
            query_vector=query_vector,
            query_filter=query_filter,
            threshold=threshold,
            limit=limit,
            offset=offset,
            with_vectors=with_vectors,
            with_payload=with_payload,
        )

    @classmethod
    def _build_field_condition(cls, key: str, value: object) -> models.FieldCondition:
        if isinstance(value, Iterable) and not isinstance(value, str | bytes | dict):
            match = models.MatchAny(any=value)
        else:
            match = models.MatchValue(value=value)

        return models.FieldCondition(key=key, match=match)

    @classmethod
    def _get_filter_condition(
        cls,
        include_filter_map: dict | None = None,
        exclude_filter_map: dict | None = None,
    ) -> Filter:
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

    @classmethod
    async def _search(
        cls,
        client: AsyncQdrantClient,
        query_vector: Sequence[float],
        query_filter: Filter,
        threshold: float,
        limit: int,
        offset: int,
        with_vectors: bool,
        with_payload: list[str],
    ) -> list[ScoredPoint]:
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
    async def retrieve(
        cls,
        client: AsyncQdrantClient,
        retrieve_list: list[str],
        with_vectors: bool = True,
        with_payload: list[str] | bool = True,
    ) -> list[Record]:
        return await client.retrieve(
            collection_name=cls.get_full_collection_name(),
            ids=retrieve_list,
            with_vectors=with_vectors,
            with_payload=with_payload,
        )

    @classmethod
    def _make_payload(cls, payload_dict: dict[str, Any]) -> dict[str, Any]:
        return {
            payload_column: payload_dict[payload_column] for payload_column in cls.PAYLOAD_COLUMNS
        }
