import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pensabot.models import Chat
from pensabot.storage.db import Database


class Chats:
    """Persist and retrieve recent chat messages from PostgreSQL."""

    def __init__(self, database: Database, recent_message_limit: int) -> None:
        self._database = database
        self._recent_message_limit = recent_message_limit
        self._conversation_locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def conversation(self, conversation_id: str) -> AsyncIterator[None]:
        """Serialize messages for one conversation within this process."""
        lock = self._conversation_locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:
            yield

    async def load_recent(self, conversation_id: str) -> list[Chat]:
        query = """
            SELECT id, user_id, conversation_id, role, content, created_at
            FROM (
                SELECT id, user_id, conversation_id, role, content, created_at
                FROM chats
                WHERE conversation_id = %s
                ORDER BY id DESC
                LIMIT %s
            ) AS recent_messages
            ORDER BY id
        """
        async with self._database.connection() as connection:
            cursor = await connection.execute(
                query,
                (conversation_id, self._recent_message_limit),
            )
            rows = await cursor.fetchall()

        return [Chat(*row) for row in rows]

    async def append_exchange(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        agent_message: str,
    ) -> None:
        query = """
            INSERT INTO chats (user_id, conversation_id, role, content)
            VALUES
                (%s, %s, 'user', %s),
                (%s, %s, 'agent', %s)
        """
        async with self._database.connection() as connection:
            await connection.execute(
                query,
                (
                    user_id,
                    conversation_id,
                    user_message,
                    user_id,
                    conversation_id,
                    agent_message,
                ),
            )
