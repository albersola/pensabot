from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Log:
    id: int
    user_id: str | None
    conversation_id: str | None
    event: str
    details: dict[str, object]
    created_at: datetime
