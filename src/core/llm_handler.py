from collections.abc import AsyncGenerator

import attr
from openai.types.chat import ChatCompletionChunk

from agent.client import async_ollama_client, async_openai_client


@attr.s(auto_attribs=True)
class LLMHandler:
    llm_name: str
    llm_source: str
    api_key: str | None

    def __attrs_post_init__(self) -> None:
        self.MODEL_REGISTRY = {
            'openai': self._chat_with_openai,
            'ollama': self._chat_with_ollama,
        }

    def get_llm_chat_func(self) -> callable:
        return self.MODEL_REGISTRY[self.llm_source]

    async def _chat_with_openai(
        self, prompt: str, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        async with async_openai_client(api_key=self.api_key) as client:
            history[-1] = {
                'role': 'user',
                'content': prompt,
            }
            async for chunk in await client.chat.completions.create(
                model=self.llm_name,
                messages=history,
                stream=True,
            ):
                if isinstance(chunk, ChatCompletionChunk):
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content

    async def _chat_with_ollama(
        self, prompt: str, history: list[dict]
    ) -> AsyncGenerator[str, None]:
        async with async_ollama_client() as client:
            history[-1] = {
                'role': 'user',
                'content': prompt,
            }
            async for chunk in await client.chat(
                model=self.llm_name,
                messages=history,
                stream=True,
            ):
                yield chunk['message']['content']
