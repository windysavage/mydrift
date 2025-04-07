import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api.schema import IngestGmailPayload, IngestMessagePayload
from api.utils import get_embedding_model
from core.reindex_handler import ReindexHandler

ingest_router = APIRouter(prefix='/ingest', tags=['ingest'])


async def reindex_stream_response(
    documents: list[dict], embedding_model: object
) -> AsyncGenerator[int, None]:
    handler = ReindexHandler(
        documents=documents,
        embedding_model=embedding_model,
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


@ingest_router.post('/message')
async def ingest_message(
    payload: IngestMessagePayload,
    embedding_model: object = Depends(get_embedding_model),
) -> dict:
    documents = payload.documents

    return StreamingResponse(
        reindex_stream_response(documents, embedding_model), media_type='text/plain'
    )


@ingest_router.post('/gmail')
def ingest(request: IngestGmailPayload) -> None:
    print(request)
