import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

from pensabot.brain import AgentDependencies, remember_memory, retrieve_memories
from pensabot.models import Memory


class RememberMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_saves_memory_for_current_user_and_logs_event(self) -> None:
        memory = Mock(id=12, memory_key="profile.name")
        memories = Mock()
        memories.upsert = AsyncMock(return_value=memory)
        logs = Mock()
        logs.append = AsyncMock()
        context = Mock(
            deps=AgentDependencies(
                memories=memories,
                logs=logs,
                user_id="telegram:456",
                conversation_id="telegram:123",
            )
        )

        result = await remember_memory(
            context,
            memory_key=" Profile.Name ",
            content=" The user's name is Alberto. ",
        )

        self.assertEqual(result, "Memory saved with key 'profile.name'")
        memories.upsert.assert_awaited_once_with(
            user_id="telegram:456",
            memory_key="profile.name",
            content="The user's name is Alberto.",
            source_conversation_id="telegram:123",
        )
        logs.append.assert_awaited_once_with(
            event="memory.saved",
            user_id="telegram:456",
            conversation_id="telegram:123",
            details={"memory_id": 12, "memory_key": "profile.name"},
        )


class RetrieveMemoriesTests(unittest.IsolatedAsyncioTestCase):
    async def test_retrieves_current_user_memories_and_logs_event(self) -> None:
        memory = Memory(
            id=12,
            user_id="telegram:456",
            memory_key="project.pensabot",
            content="Pensabot uses PostgreSQL for durable memories.",
            source_conversation_id="telegram:123",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 2, 1, tzinfo=UTC),
        )
        memories = Mock()
        memories.search = AsyncMock(return_value=[memory])
        logs = Mock()
        logs.append = AsyncMock()
        context = Mock(
            deps=AgentDependencies(
                memories=memories,
                logs=logs,
                user_id="telegram:456",
                conversation_id="telegram:123",
            )
        )

        result = await retrieve_memories(
            context,
            query="  PostgreSQL memories  ",
        )

        self.assertEqual(
            result,
            "Matching memories:\n"
            "- [project.pensabot] Pensabot uses PostgreSQL for durable memories.",
        )
        memories.search.assert_awaited_once_with(
            user_id="telegram:456",
            query="PostgreSQL memories",
        )
        logs.append.assert_awaited_once_with(
            event="memory.search",
            user_id="telegram:456",
            conversation_id="telegram:123",
            details={
                "query": "PostgreSQL memories",
                "memory_ids": [12],
                "result_count": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
