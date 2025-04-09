from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.schema import MessagePayload
from api.utils import get_encoder, safe_stream_wrapper
from core.agent_handler import AgentHandler
from core.llm_handler import LLMHandler

chat_router = APIRouter(prefix='/chat', tags=['chat'])


@safe_stream_wrapper
async def chat_stream_response(
    message: str,
    llm_name: str,
    llm_source: str,
    api_key: str | None,
    user_name: str | None,
    encoder: object,
) -> AsyncGenerator[str, None]:
    llm_handler = LLMHandler(llm_name=llm_name, llm_source=llm_source, api_key=api_key)
    llm_chat_func = llm_handler.get_llm_chat_func()

    agent_handler = AgentHandler(
        user_name=user_name,
        encoder=encoder,
        llm_chat_func=llm_chat_func,
    )
    response = agent_handler.get_chat_response(message=message)
    async for token in response:
        yield token


@chat_router.post('/chat-with-agent')
async def chat_with_agent(
    payload: MessagePayload,
    encoder: object = Depends(get_encoder),
) -> dict:
    return StreamingResponse(
        chat_stream_response(
            message=payload.message,
            llm_name=payload.llm_name,
            llm_source=payload.llm_source,
            api_key=payload.api_key,
            user_name=payload.user_name,
            encoder=encoder,
        ),
        media_type='text/plain',
    )
