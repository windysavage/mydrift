from collections.abc import AsyncGenerator

import attr
from qdrant_client import AsyncQdrantClient

from agent.chat_agent import ChatAgent


@attr.s(auto_attribs=True)
class AgentHandler:
    username: str
    qdrant_client: AsyncQdrantClient
    embedding_model: object
    llm_chat_func: callable

    async def get_chat_response(self, message: str) -> AsyncGenerator[str, None]:
        chat_agent = ChatAgent(
            username=self.username,
            qdrant_client=self.qdrant_client,
            embedding_model=self.embedding_model,
            llm_chat_func=self.llm_chat_func,
        )
        async for token in chat_agent.generate_response(query=message):
            yield token
