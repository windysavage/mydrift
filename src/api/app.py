import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from api.schema import MessagePayload, UploadJsonPayload
from core.chat_handler import ChatHandler
from core.reindex_handler import ReindexHandler
from database.mongodb.base import init_mongodb_cols
from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client
from database.qdrant.base import init_qdrant_cols
from database.qdrant.client import async_qdrant_client
from embedding.loader import load_embedding_model_by_name

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_qdrant_cols()
    await init_mongodb_cols()
    app.state.embedding_model = load_embedding_model_by_name()
    yield
    print('🛑 Shutting down...')


app = FastAPI(lifespan=lifespan)


async def chat_stream_response(
    message: str, llm_name: str, llm_source: str
) -> AsyncGenerator[str, None]:
    async with async_qdrant_client() as client:
        handler = ChatHandler(
            username='RH Huang',
            qdrant_client=client,
            embedding_model=app.state.embedding_model,
            llm_name=llm_name,
            llm_source=llm_source,
        )
        response = handler.get_chat_response(message, llm_name, llm_source)
        async for token in response:
            yield token


async def reindex_stream_response(documents: list[dict]) -> AsyncGenerator[int, None]:
    handler = ReindexHandler(
        documents=documents,
        embedding_model=app.state.embedding_model,
        window_sizes=[5],
        stride=3,
    )
    response = handler.index_message_chunks()
    async for indexed_doc_count in response:
        yield (
            json.dumps(
                {
                    'status': 'ok',
                    'total_doc_count': len(documents),
                    'indexed_doc_count': indexed_doc_count,
                }
            )
            + '\n'
        )


@app.post('/chat')
async def chat_with_agent(request: MessagePayload) -> dict:
    return StreamingResponse(
        chat_stream_response(
            message=request.message,
            llm_name=request.llm_name,
            llm_source=request.llm_source,
        ),
        media_type='text/plain',
    )


@app.post('/upload-json')
async def upload_json(payload: UploadJsonPayload) -> dict:
    documents = payload.documents

    return StreamingResponse(
        reindex_stream_response(documents), media_type='text/plain'
    )


@app.get('/get-docs')
async def get_docs(page: int, page_size: int) -> dict:
    async with async_mongodb_client() as client:
        return await ChatDoc.scroll(client=client, page=page, page_size=page_size)


@app.get('/health_check')
def health_check() -> None:
    return {'message': 'Hello, FastAPI! Bonjur!'}
