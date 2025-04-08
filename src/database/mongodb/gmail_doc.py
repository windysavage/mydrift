from collections.abc import Generator

from database.mongodb.base import BaseDocCol


class GmailDoc(BaseDocCol):
    DATABASE_NAME = 'mydrift'
    COLLECTION_BASE_NAME = 'gmail_collection'
    COLLECTION_VERSION_NAME = '2025-04-08'
    INDEX_FIELDS_WITH_DIRECTION = []

    @classmethod
    def prepare_iter_docs(cls, chunks: list[dict], batch_size: int = 250) -> Generator:
        docs = []
        for chunk in chunks:
            doc = {
                'doc_id': chunk['chunk_id'],
                'on_date': chunk['on_date'],
                'text': chunk['text'],
            }
            docs.append(doc)

            if len(docs) == batch_size:
                yield docs
                docs = []

        if docs:
            yield docs
