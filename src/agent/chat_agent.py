from collections.abc import AsyncGenerator

import attr
from qdrant_client.conversions.common_types import ScoredPoint

from database.qdrant.chat_vec import ChatVec


@attr.s()
class ChatAgent:
    user_name: str | None = attr.ib()
    qdrant_client: object = attr.ib()
    embedding_model: object = attr.ib()
    llm_chat_func: callable = attr.ib()

    def _construct_prompt(self, query: str, context: str) -> str:
        return (
            f'我是 {self.user_name}，因此所有以{self.user_name}開頭的訊息都是我說的。'
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
            include_filter_map={'senders': self.user_name},
        )
        return results

    async def retrieve_context(self, query: str, context_window: int = 30) -> str:
        query_embedding = self.embedding_model.encode([query])[0]
        results = await self._retrieve_similar_messages(
            embedding=query_embedding.tolist(), limit=context_window
        )
        context = ' '.join([result.payload['text'] for result in results])
        return context

    async def generate_response(
        self, query: str, context_window: int = 3
    ) -> AsyncGenerator[str, None]:
        context = await self.retrieve_context(query, context_window=context_window)
        async for token in self.llm_chat_func(
            prompt=self._construct_prompt(query=query, context=context)
        ):
            yield token
