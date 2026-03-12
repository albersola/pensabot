from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class ExternalAccount(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str
    provider_user_id: str
    username: str | None = None
    linked_at: datetime = Field(default_factory=datetime.utcnow)
