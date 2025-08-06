from collections.abc import AsyncGenerator

import attr

from agent.chat_agent import ChatAgent
from embedding.base import EncoderProtocol


@attr.s(auto_attribs=True)
class AgentHandler:
    user_name: str | None
    encoder: EncoderProtocol
    llm_chat_func: callable

    async def get_chat_response(
        self, message: str, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        chat_agent = ChatAgent(
            user_name=self.user_name,
            encoder=self.encoder,
            llm_chat_func=self.llm_chat_func,
        )
        async for token in chat_agent.generate_response(query=message, history=history):
            yield token
