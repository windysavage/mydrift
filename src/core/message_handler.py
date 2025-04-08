from collections.abc import AsyncGenerator

import attr

from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client
from database.qdrant.client import async_qdrant_client
from database.qdrant.rag_vec_store import RAGVecStore
from utils import decode_content, generate_message_chunk_id, mask_urls

SOURCE = 'message'


@attr.s(auto_attribs=True)
class MessageHandler:
    documents: list[dict]
    embedding_model: object
    window_sizes: list[int] = [5]
    stride: int = 1

    async def index_message_chunks(
        self,
        dry_run: bool = False,
        batch_size: int = 250,
    ) -> AsyncGenerator[float, None] | None:
        all_chunks = []
        for doc in self.documents:
            chunks = await self._process_single_document(doc)
            all_chunks += chunks

        if not dry_run:
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            batch_count = 0
            async with async_qdrant_client() as client:
                async for _ in RAGVecStore.iter_upsert_points(
                    client=client,
                    batched_iter_points=RAGVecStore.prepare_iter_points(
                        [
                            {
                                'chunk_id': chunk['chunk_id'],
                                'embedding': chunk['embedding'],
                                'source': SOURCE,
                            }
                            for chunk in all_chunks
                        ]
                    ),
                ):
                    pass
            async with async_mongodb_client() as client:
                async for _ in ChatDoc.iter_upsert_docs(
                    client=client, docs=ChatDoc.prepare_iter_docs(all_chunks)
                ):
                    batch_count += 1
                await ChatDoc.create_index(client=client)
            yield batch_count / total_batches

    async def _process_single_document(self, document: dict) -> list[dict]:
        messages = [
            msg for msg in document.get('messages', []) if self._is_text_message(msg)
        ]

        if not messages:
            return

        senders = [
            decode_content(participant.get('name', ''))
            for participant in document.get('participants', [])
        ]

        chunks = self._build_chunks(senders=senders, messages=messages)
        text_list = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(
            sentences=text_list, show_progress_bar=True
        )

        for idx, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[idx]

        return chunks

    def _build_chunks(self, senders: list[str], messages: list[dict]) -> list[dict]:
        messages.sort(key=lambda x: x['timestamp_ms'])
        chunks = []

        for window_size in self.window_sizes:
            for i in range(0, len(messages) - window_size + 1, self.stride):
                window = messages[i : i + window_size]
                chunk_text = self._merge_messages_to_chunk(window)
                chunk_text = mask_urls(decode_content(chunk_text))

                chunk = {
                    'chunk_id': generate_message_chunk_id(
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
