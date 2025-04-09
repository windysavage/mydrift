import functools
import json
import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

ERROR_STATUS_KEY = 'status'
ERROR_MESSAGE_KEY = 'message'
ERROR_VALUE = 'error_value'


def get_encoder(request: Request) -> object:
    return request.app.state.encoder


def safe_stream_wrapper(
    func: Callable[..., AsyncGenerator[Any, None]],
    *,
    error_status_key: str = ERROR_STATUS_KEY,
    error_message_key: str = ERROR_MESSAGE_KEY,
    error_value: str = 'error',
) -> Callable[..., AsyncGenerator[str, None]]:
    @functools.wraps(func)
    async def wrapper(*args: list, **kwargs: dict) -> AsyncGenerator[Any, None]:
        try:
            async for item in func(*args, **kwargs):
                yield item
        except Exception as e:
            logging.exception('Streaming 發生未預期錯誤')
            yield (
                json.dumps(
                    {
                        error_status_key: error_value,
                        error_message_key: str(e),
                    }
                )
                + '\n'
            )

    return wrapper


def safe_async_wrapper(
    func: Callable[..., Coroutine[Any, Any, Any]],
    *,
    status_code: int = 500,
    error_status_key: str = ERROR_STATUS_KEY,
    error_message_key: str = ERROR_MESSAGE_KEY,
    error_value: str = 'error',
) -> Callable[..., Coroutine[Any, Any, JSONResponse]]:
    @functools.wraps(func)
    async def wrapper(*args: dict, **kwargs: dict) -> object:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logging.exception('API handler 發生未預期錯誤')
            return JSONResponse(
                status_code=status_code,
                content={
                    error_status_key: error_value,
                    error_message_key: str(e),
                },
            )

    return wrapper
