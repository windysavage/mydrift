from pydantic import BaseModel


class MessagePayload(BaseModel):
    message: str
