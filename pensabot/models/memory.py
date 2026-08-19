from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Memory:
    id: int
    user_id: str
    memory_key: str
    content: str
    source_conversation_id: str
    created_at: datetime
    updated_at: datetime
