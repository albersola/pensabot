import unittest
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from pensabot.brain import AgentDependencies
from pensabot.core import handle_message
from pensabot.models import Chat


class FakeChats:
    def __init__(self, recent_messages: list[Chat]) -> None:
        self.recent_messages = recent_messages
        self.loaded_conversation_id: str | None = None
        self.appended_exchange: tuple[str, str, str, str] | None = None

    @asynccontextmanager
    async def conversation(self, conversation_id: str) -> AsyncIterator[None]:
        yield

    async def load_recent(self, conversation_id: str) -> list[Chat]:
        self.loaded_conversation_id = conversation_id
        return self.recent_messages

    async def append_exchange(
        self,
        user_id: str,
        conversation_id: str,
        user_message: str,
        agent_message: str,
    ) -> None:
        self.appended_exchange = (
            user_id,
            conversation_id,
            user_message,
            agent_message,
        )


class HandleMessageTests(unittest.IsolatedAsyncioTestCase):
    @patch("pensabot.core.brain.run", new_callable=AsyncMock)
    async def test_uses_recent_messages_and_persists_exchange(
        self,
        run_mock: AsyncMock,
    ) -> None:
        run_mock.return_value = Mock(output="organized idea")
        memories = Mock()
        logs = Mock()
        chats = FakeChats(
            [
                Chat(
                    id=1,
                    user_id="telegram:456",
                    conversation_id="telegram:123",
                    role="user",
                    content="earlier idea",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                Chat(
                    id=2,
                    user_id="telegram:456",
                    conversation_id="telegram:123",
                    role="agent",
                    content="earlier response",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
            ]
        )

        response = await handle_message(
            "an idea",
            "telegram:456",
            "telegram:123",
            chats,
            memories,
            logs,
        )

        self.assertEqual(response, "organized idea")
        run_mock.assert_awaited_once()
        run_arguments, run_keyword_arguments = run_mock.await_args
        self.assertEqual(run_arguments, ("an idea",))
        self.assertEqual(
            run_keyword_arguments["deps"],
            AgentDependencies(
                memories=memories,
                logs=logs,
                user_id="telegram:456",
                conversation_id="telegram:123",
            ),
        )
        message_history = run_keyword_arguments["message_history"]
        self.assertEqual(len(message_history), 2)
        self.assertIsInstance(message_history[0], ModelRequest)
        self.assertIsInstance(message_history[0].parts[0], UserPromptPart)
        self.assertEqual(message_history[0].parts[0].content, "earlier idea")
        self.assertIsInstance(message_history[1], ModelResponse)
        self.assertIsInstance(message_history[1].parts[0], TextPart)
        self.assertEqual(message_history[1].parts[0].content, "earlier response")
        self.assertEqual(chats.loaded_conversation_id, "telegram:123")
        self.assertEqual(
            chats.appended_exchange,
            ("telegram:456", "telegram:123", "an idea", "organized idea"),
        )


if __name__ == "__main__":
    unittest.main()
