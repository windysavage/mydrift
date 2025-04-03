from collections.abc import Iterable

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne


class BaseDocCol:
    def __init_subclass__(cls, **kwargs: dict) -> None:
        super().__init_subclass__(**kwargs)
        required_attrs = [
            'COLLECTION_BASE_NAME',
            'COLLECTION_VERSION_NAME',
            'DATABASE_NAME',
        ]
        for attr in required_attrs:
            if getattr(cls, attr, None) is None:
                raise TypeError(f'Class `{cls.__name__}` must define `{attr}`')

        cls.check_cls_config()

    @classmethod
    def check_cls_config(cls) -> None:
        assert isinstance(cls.DATABASE_NAME, str)
        assert isinstance(cls.COLLECTION_BASE_NAME, str)
        assert isinstance(cls.COLLECTION_VERSION_NAME, str)

    @classmethod
    def get_full_collection_name(cls) -> str:
        return f'{cls.COLLECTION_BASE_NAME}-{cls.COLLECTION_VERSION_NAME}'

    @classmethod
    async def create_collection(cls, client: AsyncIOMotorClient) -> None:
        db = client[cls.DATABASE_NAME]
        full_collection_name = cls.get_full_collection_name()

        existing_collections = await db.list_collection_names()
        if full_collection_name not in existing_collections:
            try:
                await db.create_collection(full_collection_name)
            except Exception as e:
                raise RuntimeError(
                    f'Failed to create collection "{full_collection_name}"'
                ) from e

    @classmethod
    async def iter_upsert_docs(
        cls, client: AsyncIOMotorClient, docs: Iterable[list[dict]]
    ) -> None:
        db = client[cls.DATABASE_NAME]
        full_collection_name = cls.get_full_collection_name()

        for batched_doc in docs:
            operations = [
                UpdateOne(
                    {'_id': doc['doc_id']},
                    {'$set': doc},
                    upsert=True,
                )
                for doc in batched_doc
            ]

            if operations:
                await db[full_collection_name].bulk_write(operations, ordered=False)
