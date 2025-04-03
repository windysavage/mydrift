from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from agent.chat_agent import ChatAgent
from api.schema import MessagePayload, UploadJsonPayload
from database.qdrant.client import async_qdrant_client
from embedding.loader import load_embedding_model_by_name

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


@app.post('/upload-json')
async def upload_json(payload: UploadJsonPayload) -> dict:
    memory_name = payload.memory_name
    documents = payload.documents

    # 在這裡可以：清除 Qdrant index、處理資料、嵌入、存入 Qdrant 等
    print(f'[info] 收到記憶庫：{memory_name}，共 {len(documents)} 筆 JSON 文件')

    return {
        'status': 'ok',
        'memory_name': memory_name,
        'count': len(documents),
    }


@app.get('/health_check')
def health_check() -> None:
    return {'message': 'Hello, FastAPI! Bonjur!'}
