from typing import Any

from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str


class UploadJsonPayload(BaseModel):
    memory_name: str
    documents: list[dict[str, Any]]
