from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlmodel import Field, SQLModel

from config import settings


class Memory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    content: str
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(settings.embedding_dimensions)),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
