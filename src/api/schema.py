from typing import Any

from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str
    llm_name: str = 'gpt-4o-mini'
    llm_source: str = 'openai'
    api_key: str | None = None
    user_name: str | None = None


class UploadJsonPayload(BaseModel):
    documents: list[dict[str, Any]]


class GmailOAuthPayload(BaseModel):
    client_id: str
    client_secret: str


class IngestGmailPayload(BaseModel):
    access_token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
