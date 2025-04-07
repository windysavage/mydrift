from fastapi import APIRouter

from database.mongodb.chat_doc import ChatDoc
from database.mongodb.client import async_mongodb_client

memory_router = APIRouter(prefix='/memory', tags=['memory'])


@memory_router.get('/get-paginated-docs')
async def get_paginated_docs(page: int, page_size: int, senders: str = '') -> dict:
    async with async_mongodb_client() as client:
        return await ChatDoc.scroll(
            client=client, page=page, page_size=page_size, senders=senders
        )


@memory_router.get('/get-page-count')
async def get_page_count(page_size: int = 3, senders: str = '') -> dict:
    async with async_mongodb_client() as client:
        return {
            'total_pages': await ChatDoc.get_page_count(
                client=client, page_size=page_size, senders=senders
            )
        }
