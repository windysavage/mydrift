from collections.abc import AsyncGenerator

import attr

from agent.base import BaseAgent
from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client
from database.mongodb.gmail_doc import GmailDoc
from database.qdrant.client import async_qdrant_client
from database.qdrant.rag_vec_store import RAGVecStore
from embedding.base import EncoderProtocol


@attr.s()
class ChatAgent(BaseAgent):
    user_name: str | None = attr.ib()
    encoder: EncoderProtocol = attr.ib()
    llm_chat_func: callable = attr.ib()

    def _construct_prompt(self, query: str, context: str) -> str:
        prompt_template = self._load_prompt(
            prompt_source='chat_agent_prompts.toml', prompt_name='memory_recall_prompt'
        )
        return prompt_template.format(
            user_name=self.user_name, query=query, context=context
        )

    async def _get_text_list_by_source(self, source: str, ids: list[str]) -> list[str]:
        if source == 'message':
            source_cls = ChatDoc
        elif source == 'gmail':
            source_cls = GmailDoc
        else:
            raise ValueError('There is no {source} source!}')

        async with async_mongodb_client() as client:
            chunks = await source_cls.get_doc_by_ids(
                client=client, ids=[_id.replace('-', '') for _id in ids]
            )
        return [chunk['text'] for chunk in chunks]

    async def _retrieve_similar_messages(
        self, embedding: list[float], limit: int = 5
    ) -> list[str]:
        async with async_qdrant_client() as client:
            vector_results = await RAGVecStore.search(
                client=client,
                query_vector=embedding,
                limit=limit,
                with_payload=['source'],
            )

        text_list = []
        for source in ['message', 'gmail']:
            vector_ids = [
                vector_result.id
                for vector_result in vector_results
                if vector_result.payload['source'] == source
            ]
            text_list += await self._get_text_list_by_source(source, vector_ids)

        return text_list

    async def _retrieve_context(self, query: str, context_window: int = 30) -> str:
        query_embedding = self.encoder.encode([query])[0]
        results = await self._retrieve_similar_messages(
            embedding=query_embedding.tolist(), limit=context_window
        )
        return ' '.join(results)

    async def generate_response(
        self, query: str, history: list[dict], context_window: int = 3
    ) -> AsyncGenerator[str, None]:
        context = await self._retrieve_context(query, context_window=context_window)
        async for token in self.llm_chat_func(
            prompt=self._construct_prompt(query=query, context=context), history=history
        ):
            yield token
