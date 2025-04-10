from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router.auth import auth_router
from api.router.chat import chat_router
from api.router.ingest import ingest_router
from api.router.memory import memory_router
from database.mongodb.base import init_mongodb_cols
from database.qdrant.base import init_qdrant_cols
from embedding.encoder import Encoder

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_qdrant_cols()
    await init_mongodb_cols()
    app.state.encoder = Encoder()
    yield
    print('🛑 Shutting down...')


app = FastAPI(lifespan=lifespan)
app.include_router(ingest_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(memory_router)


@app.get('/health_check')
def health_check() -> None:
    return {'message': 'Hello, FastAPI! Bonjur!'}
