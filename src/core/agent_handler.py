from collections.abc import AsyncGenerator

import attr
from qdrant_client import AsyncQdrantClient

from agent.chat_agent import ChatAgent
from core.llm_handler import LLMHandler


@attr.s(auto_attribs=True)
class ChatAgentHandler:
    username: str
    qdrant_client: AsyncQdrantClient
    embedding_model: object
    llm_name: str
    llm_source: str

    async def get_chat_response(
        self, message: str, llm_name: str, llm_source: str
    ) -> AsyncGenerator[str, None]:
        llm_handler = LLMHandler(llm_name=llm_name, llm_source=llm_source)
        llm_chat_func = llm_handler.get_llm_chat_func()
        chat_agent = ChatAgent(
            username=self.username,
            qdrant_client=self.qdrant_client,
            embedding_model=self.embedding_model,
            llm_chat_func=llm_chat_func,
        )
        async for token in chat_agent.generate_response(query=message):
            yield token
