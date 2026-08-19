from dataclasses import dataclass
from datetime import datetime
from typing import Literal


ChatRole = Literal["user", "agent"]


@dataclass(frozen=True)
class Chat:
    id: int
    user_id: str
    conversation_id: str
    role: ChatRole
    content: str
    created_at: datetime
