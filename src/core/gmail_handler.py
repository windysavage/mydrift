import base64
import re
from collections.abc import AsyncGenerator

import attr
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from consts import INDEX_GMAIL_MAX_RESULT
from database.mongodb.client import async_mongodb_client
from database.mongodb.gmail_doc import GmailDoc
from database.qdrant.client import async_qdrant_client
from database.qdrant.rag_vec_store import RAGVecStore
from embedding.base import EncoderProtocol
from utils import ensure_date_type, generate_gmail_chunk_id


@attr.s(auto_attribs=True)
class GmailHandler:
    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    encoder: EncoderProtocol

    def __attrs_post_init__(self) -> None:
        credentials = Credentials(
            token=self.access_token,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes,
        )
        self.service = build('gmail', 'v1', credentials=credentials)
        self.SOURCE = 'gmail'

    async def index_gmail_chunks(
        self,
        max_results: int = INDEX_GMAIL_MAX_RESULT,
        label_ids: list[str] | None = None,
        query_filter: str = '',
        dry_run: bool = False,
        batch_size: int = 250,
    ) -> AsyncGenerator[float, None] | None:
        chunks = self._fetch_recent_messages(
            max_results=max_results, label_ids=label_ids, q=query_filter
        )
        text_list = [chunk['text'] for chunk in chunks]
        embeddings = self.encoder.encode(sentences=text_list, show_progress_bar=True)

        for idx, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[idx]

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
                                'source': self.SOURCE,
                            }
                            for chunk in chunks
                        ]
                    ),
                ):
                    pass
            async with async_mongodb_client() as client:
                async for _ in GmailDoc.iter_upsert_docs(
                    client=client, docs=GmailDoc.prepare_iter_docs(chunks)
                ):
                    batch_count += 1
                await GmailDoc.create_index(client=client)

            yield batch_count / total_batches

    @staticmethod
    def decode_body(data: str) -> str:
        return base64.urlsafe_b64decode(data.encode('utf-8')).decode(
            'utf-8', errors='ignore'
        )

    @staticmethod
    def clean_empty_lines(text: str) -> str:
        return re.sub(r'\n{3,}', '\n', text).strip()

    @staticmethod
    def is_noise(text: str) -> bool:
        return not text.replace(' ', '') or all(c == '?' for c in text.replace(' ', ''))

    def _extract_plain_text_from_message(self, message: dict) -> str | None:
        payload = message.get('payload', {})

        if payload.get('mimeType') == 'text/plain' and 'body' in payload:
            data = payload['body'].get('data', '')
            return self.decode_body(data)

        for part in payload.get('parts', []):
            if part.get('mimeType') == 'text/plain':
                data = part.get('body', {}).get('data', '')
                return self.decode_body(data)

            if part.get('mimeType') == 'text/html':
                data = part.get('body', {}).get('data', '')
                html = self.decode_body(data)
                soup = BeautifulSoup(html, 'html.parser')
                return soup.get_text(separator='\n')

        return None

    def _fetch_recent_messages(
        self,
        max_results: int = INDEX_GMAIL_MAX_RESULT,
        label_ids: list[str] | None = None,
        q: str = '',
    ) -> list[dict]:
        result = (
            self.service.users()
            .messages()
            .list(
                userId='me',
                labelIds=label_ids or ['INBOX'],
                maxResults=max_results,
                q=q,
            )
            .execute()
        )

        messages = result.get('messages', [])
        chunks = []

        for msg in messages:
            message_detail = (
                self.service.users().messages().get(userId='me', id=msg['id']).execute()
            )
            plain_text = self._extract_plain_text_from_message(message_detail)

            if not plain_text or self.is_noise(plain_text):
                continue

            internal_date = int(message_detail.get('internalDate', 0))

            chunks.append(
                {
                    'chunk_id': generate_gmail_chunk_id(
                        on_date=ensure_date_type(internal_date), message_id=msg['id']
                    ),
                    'text': plain_text,
                    'on_date': ensure_date_type(internal_date),
                }
            )

        return chunks
