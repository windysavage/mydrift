from collections.abc import Generator

from database.mongodb.base import BaseDocCol


class ChatDoc(BaseDocCol):
    DATABASE_NAME = 'mydrift'
    COLLECTION_BASE_NAME = 'chat_collection'
    COLLECTION_VERSION_NAME = '2025-04-03'
    INDEX_FIELDS_WITH_DIRECTION = [('senders', 1)]

    @classmethod
    def prepare_iter_docs(cls, chunks: list[dict], batch_size: int = 250) -> Generator:
        docs = []
        for chunk in chunks:
            doc = {
                'doc_id': chunk['chunk_id'],
                'start_timestamp': chunk['start_timestamp'],
                'end_timestamp': chunk['end_timestamp'],
                'senders': chunk['senders'],
                'text': chunk['text'],
            }
            docs.append(doc)

            if len(docs) == batch_size:
                yield docs
                docs = []

        if docs:
            yield docs
