from typing import Any

from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str
    llm_name: str = 'gemma3:4b'
    llm_source: str = 'ollama'


class UploadJsonPayload(BaseModel):
    documents: list[dict[str, Any]]
