import hashlib
import re

import attr

from database.qdrant.chat_vec import ChatVec
from database.qdrant.client import async_qdrant_client


@attr.s(auto_attribs=True)
class ReindexHandler:
    documents: list[dict]
    embedding_model: object
    window_sizes: list[int] = [5]
    stride: int = 1

    async def index_message_chunks(self) -> int:
        total_chunks = 0
        for doc in self.documents:
            total_chunks += await self._process_single_document(doc)
        return total_chunks

    async def _process_single_document(self, document: dict) -> int:
        messages = [
            msg for msg in document.get('messages', []) if self._is_text_message(msg)
        ]

        if not messages:
            return 0

        senders = [
            self._decode_content(participant.get('name', ''))
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
                client=client, points=ChatVec.prepare_iter_points(chunks, embeddings)
            )

        print(f'📤 上傳 {len(chunks)} chunks')
        return len(chunks)

    def _build_chunks(self, senders: list[str], messages: list[dict]) -> list[dict]:
        messages.sort(key=lambda x: x['timestamp_ms'])
        chunks = []

        for window_size in self.window_sizes:
            for i in range(0, len(messages) - window_size + 1, self.stride):
                window = messages[i : i + window_size]
                chunk_text = self._merge_messages_to_chunk(window)
                chunk_text = self._mask_urls(self._decode_content(chunk_text))

                chunk = {
                    'chunk_id': self._generate_chunk_id(
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

    def _decode_content(self, content_str: str) -> str:
        return content_str.encode('latin1').decode('utf-8')

    def _mask_urls(self, text: str) -> str:
        return re.sub(r'https?://\S+', '[LINK]', text)

    def _generate_chunk_id(self, start_ts: int, end_ts: int, senders: list[str]) -> str:
        base = f'{start_ts}-{end_ts}-{"-".join(sorted(senders))}'
        return hashlib.md5(base.encode()).hexdigest()
