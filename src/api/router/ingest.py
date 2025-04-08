import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.schema import IngestGmailPayload, IngestMessagePayload
from api.utils import get_embedding_model, safe_stream_wrapper
from core.gmail_handler import GmailHandler
from core.message_handler import MessageHandler

ingest_router = APIRouter(prefix='/ingest', tags=['ingest'])


@safe_stream_wrapper
async def ingest_message_stream_response(
    documents: list[dict], embedding_model: object
) -> AsyncGenerator[int, None]:
    handler = MessageHandler(
        documents=documents,
        embedding_model=embedding_model,
        window_sizes=[5],
        stride=3,
    )
    response = handler.index_message_chunks()

    async for indexed_ratio in response:
        yield (
            json.dumps(
                {
                    'status': 'ok',
                    'indexed_ratio': indexed_ratio,
                }
            )
            + '\n'
        )


@safe_stream_wrapper
async def ingest_gmail_stream_response(
    access_token: str,
    refresh_token: str,
    token_uri: str,
    client_id: str,
    client_secret: str,
    scopes: list[str],
    embedding_model: object,
) -> AsyncGenerator[int, None]:
    handler = GmailHandler(
        access_token=access_token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        embedding_model=embedding_model,
    )

    response = handler.index_gmail_chunks(max_results=5, label_ids=['INBOX'])

    async for indexed_ratio in response:
        yield (
            json.dumps(
                {
                    'status': 'ok',
                    'indexed_ratio': indexed_ratio,
                }
            )
            + '\n'
        )


@ingest_router.post('/message')
async def ingest_message(
    payload: IngestMessagePayload,
    embedding_model: object = Depends(get_embedding_model),
) -> dict:
    documents = payload.documents

    return StreamingResponse(
        ingest_message_stream_response(documents, embedding_model),
        media_type='text/plain',
    )


@ingest_router.post('/gmail')
async def ingest_gmail(
    payload: IngestGmailPayload,
    embedding_model: object = Depends(get_embedding_model),
) -> None:
    return StreamingResponse(
        ingest_gmail_stream_response(
            access_token=payload.access_token,
            refresh_token=payload.refresh_token,
            token_uri=payload.token_uri,
            client_id=payload.client_id,
            client_secret=payload.client_secret,
            scopes=payload.scopes,
            embedding_model=embedding_model,
        ),
        media_type='text/plain',
    )
