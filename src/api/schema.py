from typing import Any

from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str


class UploadJsonPayload(BaseModel):
    documents: list[dict[str, Any]]
