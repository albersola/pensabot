import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

from pensabot.interfaces.telegram import create_text_handler


class CreateTextHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_passes_telegram_user_and_chat_ids(self) -> None:
        message_handler = AsyncMock(return_value="response")
        message = Mock(
            text="an idea",
            chat_id=123,
            date=datetime(2026, 1, 1, tzinfo=UTC),
            sender_chat=None,
        )
        message.reply_text = AsyncMock()
        update = Mock(
            message=message,
            channel_post=None,
            effective_chat=Mock(id=123),
            effective_user=Mock(id=456),
        )

        handler = create_text_handler({123}, message_handler)
        await handler(update, Mock())

        message_handler.assert_awaited_once_with(
            "an idea",
            "telegram:456",
            "telegram:123",
        )
        message.reply_text.assert_awaited_once_with("response")

    async def test_rejects_messages_from_unauthorized_chats(self) -> None:
        message_handler = AsyncMock(return_value="response")
        message = Mock(text="an idea")
        message.reply_text = AsyncMock()
        update = Mock(
            message=message,
            channel_post=None,
            effective_chat=Mock(id=999),
        )

        handler = create_text_handler({123}, message_handler)
        await handler(update, Mock())

        message_handler.assert_not_awaited()
        message.reply_text.assert_not_awaited()

    async def test_rejects_updates_without_an_effective_chat(self) -> None:
        message_handler = AsyncMock(return_value="response")
        message = Mock(text="an idea")
        message.reply_text = AsyncMock()
        update = Mock(
            message=message,
            channel_post=None,
            effective_chat=None,
        )

        handler = create_text_handler({123}, message_handler)
        await handler(update, Mock())

        message_handler.assert_not_awaited()
        message.reply_text.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
