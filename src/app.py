from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from agent.chat_agent import ChatAgent
from database.qdrant.client import async_qdrant_client
from embedding.loader import load_embedding_model_by_name
from schema.chat import MessagePayload

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    app.state.embedding_model = load_embedding_model_by_name()
    yield
    print('🛑 Shutting down...')


app = FastAPI(lifespan=lifespan)


async def chat_stream_response(message: str) -> AsyncGenerator[str, None]:
    async with async_qdrant_client() as client:
        chat_agent = ChatAgent(
            username='RH Huang',
            qdrant_client=client,
            embedding_model=app.state.embedding_model,
            llm_model_name='gemma3:4b',
        )
        response = chat_agent.generate_response(query=message)
        async for word in response:
            yield word


@app.post('/chat')
async def chat_with_agent(request: MessagePayload) -> dict:
    message = request.message
    return StreamingResponse(chat_stream_response(message), media_type='text/plain')


@app.get('/health_check')
def health_check() -> None:
    return {'message': 'Hello, FastAPI! Bonjur!'}
