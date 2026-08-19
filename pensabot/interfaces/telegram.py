import logging
from collections.abc import Awaitable, Callable, Collection
from functools import wraps

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from pensabot.config import TelegramConfig
from pensabot.core import handle_message
from pensabot.storage import Chats, Database, Logs, Memories

TelegramHandler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
TextMessageHandler = Callable[[str, str, str], Awaitable[str]]


def restricted(
    allowed_chat_ids: Collection[int],
) -> Callable[[TelegramHandler], TelegramHandler]:
    def decorator(handler: TelegramHandler) -> TelegramHandler:
        @wraps(handler)
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            chat = update.effective_chat
            if chat is None:
                logging.warning("Access denied for update without an effective chat")
                return

            if chat.id not in allowed_chat_ids:
                logging.warning("Unauthorized access denied for chat %s", chat.id)
                return

            await handler(update, context)

        return wrapped

    return decorator


def create_text_handler(
    allowed_chat_ids: Collection[int],
    message_handler: TextMessageHandler,
) -> TelegramHandler:
    @restricted(allowed_chat_ids)
    async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.message or update.channel_post
        if message is None or message.text is None:
            return

        sender = update.effective_user or message.sender_chat
        sender_id = sender.id if sender is not None else message.chat_id
        print(f"{sender_id} - {message.date.isoformat()} - {message.text}")

        response = await message_handler(
            message.text,
            f"telegram:{sender_id}",
            f"telegram:{message.chat_id}",
        )
        await message.reply_text(response)

    return receive_text


def run_telegram(
    config: TelegramConfig,
    database: Database,
    chats: Chats,
    memories: Memories,
    logs: Logs,
) -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    async def open_database(_: object) -> None:
        await database.open()

    async def close_database(_: object) -> None:
        await database.close()

    async def process_message(
        text: str,
        user_id: str,
        conversation_id: str,
    ) -> str:
        return await handle_message(
            text,
            user_id,
            conversation_id,
            chats,
            memories,
            logs,
        )

    application = (
        ApplicationBuilder()
        .token(config.api_key)
        .post_init(open_database)
        .post_shutdown(close_database)
        .build()
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            create_text_handler(config.allowed_chat_ids, process_message),
        )
    )
    application.run_polling()
