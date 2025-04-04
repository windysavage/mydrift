from typing import Any

from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str
    llm_name: str = 'gpt-4o-mini'
    llm_source: str = 'openai'
    api_key: str | None = None


class UploadJsonPayload(BaseModel):
    documents: list[dict[str, Any]]
