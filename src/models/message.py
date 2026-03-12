from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

MESSAGE_STATUS_PENDING = "pending"
MESSAGE_STATUS_PREPROCESSING = "preprocessing"
MESSAGE_STATUS_DONE = "done"
MESSAGE_STATUS_ERROR = "error"
MESSAGE_STATUSES = {
    MESSAGE_STATUS_PENDING,
    MESSAGE_STATUS_PREPROCESSING,
    MESSAGE_STATUS_DONE,
    MESSAGE_STATUS_ERROR,
}


class MessageType(str, Enum):
    text = "text"
    image = "image"
    voice = "voice"


class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    external_account_id: int | None = Field(default=None, foreign_key="externalaccount.id")
    provider: str
    provider_chat_id: str
    content: str = ""
    message_type: MessageType = MessageType.text
    file_url: str | None = None
    processed_content: str | None = None
    response: str | None = None
    status: str = Field(default=MESSAGE_STATUS_PENDING)
    error_detail: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
