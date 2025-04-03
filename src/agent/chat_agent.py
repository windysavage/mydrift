from collections.abc import AsyncGenerator

import attr
from openai.types.responses import ResponseTextDeltaEvent
from qdrant_client.conversions.common_types import ScoredPoint

from agent.client import async_ollama_client, async_openai_client
from database.qdrant.chat_vec import ChatVec


@attr.s()
class ChatAgent:
    username: str = attr.ib()
    qdrant_client: object = attr.ib()
    embedding_model: object = attr.ib()
    llm_name: str = attr.ib(default='gpt-4o')
    llm_source: str = attr.ib(default='openai')

    def __attrs_post_init__(self) -> None:
        self.MODEL_REGISTRY = {
            'openai': self._chat_with_openai,
            'ollama': self._chat_with_ollama,
        }

    def _construct_prompt(self, query: str, context: str) -> str:
        return (
            f'我是 {self.username}，因此所有以{self.username}開頭的訊息都是我說的。'
            f'這裡有我之前的回憶：{context}，'
            f'請根據我之前的回憶，回答我下列問題：{query}，'
            '請自行判斷是否需要參考回憶作答'
            '請全部用繁體中文回答。'
        )

    async def _retrieve_similar_messages(
        self, embedding: list[float], limit: int = 5
    ) -> list[ScoredPoint]:
        results = await ChatVec.search(
            client=self.qdrant_client,
            query_vector=embedding,
            limit=limit,
            include_filter_map={'senders': self.username},
        )
        return results

    async def retrieve_context(self, query: str, context_window: int = 30) -> str:
        query_embedding = self.embedding_model.encode([query])[0]
        results = await self._retrieve_similar_messages(
            embedding=query_embedding.tolist(), limit=context_window
        )
        context = ' '.join([result.payload['text'] for result in results])
        return context

    async def _chat_with_openai(
        self, query: str, context: str
    ) -> AsyncGenerator[str, None]:
        async with async_openai_client() as client:
            async for chunk in await client.responses.create(
                model=self.llm_name,
                input=self._construct_prompt(query=query, context=context),
                stream=True,
            ):
                if isinstance(chunk, ResponseTextDeltaEvent):
                    yield chunk.delta

    async def _chat_with_ollama(
        self, query: str, context: str
    ) -> AsyncGenerator[str, None]:
        async with async_ollama_client() as client:
            async for chunk in await client.generate(
                model=self.llm_name,
                prompt=self._construct_prompt(query=query, context=context),
                stream=True,
            ):
                yield chunk['response']

    async def generate_response(
        self, query: str, context_window: int = 3
    ) -> AsyncGenerator[str, None]:
        context = await self.retrieve_context(query, context_window=context_window)
        chat_func = self.MODEL_REGISTRY[self.llm_source]
        async for token in chat_func(query=query, context=context):
            yield token
