from collections.abc import AsyncGenerator

import attr

from core.utils import decode_content, generate_chunk_id, mask_urls
from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client
from database.qdrant.chat_vec import ChatVec
from database.qdrant.client import async_qdrant_client


@attr.s(auto_attribs=True)
class ReindexHandler:
    documents: list[dict]
    embedding_model: object
    window_sizes: list[int] = [5]
    stride: int = 1

    async def index_message_chunks(self) -> AsyncGenerator[int, None]:
        for idx, doc in enumerate(self.documents):
            await self._process_single_document(doc)
            yield idx + 1

    async def _process_single_document(self, document: dict) -> int:
        messages = [
            msg for msg in document.get('messages', []) if self._is_text_message(msg)
        ]

        if not messages:
            return 0

        senders = [
            decode_content(participant.get('name', ''))
            for participant in document.get('participants', [])
        ]

        chunks = self._build_chunks(senders=senders, messages=messages)
        if not chunks:
            return 0

        text_list = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(
            sentences=text_list, show_progress_bar=True
        )

        async with async_qdrant_client() as client:
            await ChatVec.iter_upsert_points(
                client=client,
                batched_iter_points=ChatVec.prepare_iter_points(chunks, embeddings),
            )
        async with async_mongodb_client() as client:
            await ChatDoc.iter_upsert_docs(
                client=client, docs=ChatDoc.prepare_iter_docs(chunks)
            )
            await ChatDoc.create_index(client=client)

        print(f'📤 上傳 {len(chunks)} chunks')
        return len(chunks)

    def _build_chunks(self, senders: list[str], messages: list[dict]) -> list[dict]:
        messages.sort(key=lambda x: x['timestamp_ms'])
        chunks = []

        for window_size in self.window_sizes:
            for i in range(0, len(messages) - window_size + 1, self.stride):
                window = messages[i : i + window_size]
                chunk_text = self._merge_messages_to_chunk(window)
                chunk_text = mask_urls(decode_content(chunk_text))

                chunk = {
                    'chunk_id': generate_chunk_id(
                        start_ts=window[0]['timestamp_ms'],
                        end_ts=window[-1]['timestamp_ms'],
                        senders=senders,
                    ),
                    'text': chunk_text,
                    'start_timestamp': window[0]['timestamp_ms'],
                    'end_timestamp': window[-1]['timestamp_ms'],
                    'senders': senders,
                }
                chunks.append(chunk)

        return chunks

    # --------- static-like utilities ---------

    def _is_text_message(self, message: dict) -> bool:
        return 'content' in message

    def _merge_messages_to_chunk(self, messages: list[dict]) -> str:
        return '\n'.join(f'{msg["sender_name"]}: {msg["content"]}' for msg in messages)
