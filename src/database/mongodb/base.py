from collections.abc import Iterable

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import UpdateOne

from database.mongodb.client import async_mongodb_client


async def init_mongodb_cols() -> None:
    from database.mongodb.chat_doc import ChatDoc

    all_docs = [ChatDoc]
    async with async_mongodb_client() as client:
        for col in all_docs:
            await col.create_collection(client=client)


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

    @classmethod
    async def get_page_count(
        cls,
        client: AsyncIOMotorClient,
        page_size: int,
        senders: str = '',
    ) -> int:
        db = client[cls.DATABASE_NAME]
        collection = db[cls.get_full_collection_name()]
        query_filter = {'senders': {'$all': senders.split(',')}} if senders else {}
        total = await collection.count_documents(filter=query_filter)
        return (total + page_size - 1) // page_size

    @classmethod
    async def scroll(
        cls,
        client: AsyncIOMotorClient,
        page: int = 1,
        page_size: int = 20,
        senders: str = '',
    ) -> dict:
        skip = (page - 1) * page_size
        db = client[cls.DATABASE_NAME]
        collection = db[cls.get_full_collection_name()]
        query_filter = {'senders': {'$all': senders.split(',')}} if senders else {}
        cursor = (
            collection.find(query_filter)
            .sort('start_timestamp', 1)
            .skip(skip)
            .limit(page_size)
        )

        # 把 cursor 轉為 list
        chunks = await cursor.to_list(length=page_size)
        if not chunks:
            return {}

        return {'chunks': chunks, 'page': page, 'page_size': page_size}

    @classmethod
    async def delete_docs_by_ids(
        cls, client: AsyncIOMotorClient, ids: list[str]
    ) -> None:
        db = client[cls.DATABASE_NAME]
        collection = db[cls.get_full_collection_name()]
        await collection.delete_many({'_id': {'$in': ids}})
