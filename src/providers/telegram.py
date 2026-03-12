import asyncio
from pathlib import Path

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from config import settings
from db import async_session
from models.external_account import ExternalAccount
from models.message import (
    MESSAGE_STATUS_PENDING,
    MESSAGE_STATUS_PREPROCESSING,
    Message,
    MessageType,
)
from redis_client import get_redis
from services.message_pipeline import requires_preprocessing
from services.linking import resolve_link_code

log = structlog.get_logger()


class TelegramProvider:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self._client = httpx.AsyncClient(timeout=35.0)
        self._polling = False

    async def on_message(self, payload: dict) -> None:
        message = payload.get("message")
        if not message:
            return

        chat_id = str(message["chat"]["id"])
        username = message.get("from", {}).get("username")
        text = message.get("text", "")

        # Handle /start commands before any account checks.
        if text.startswith("/start "):
            code = text.split(" ", 1)[1].strip()
            await self._handle_start(chat_id, username, code)
            return

        if text == "/start":
            await self.send_response(
                chat_id,
                f"Welcome! Register at {settings.base_url}/register and link your Telegram from the dashboard.",
            )
            return

        # Check if user is linked before any media download or processing.
        account_id: int | None = None
        user_id: int | None = None
        async with async_session() as session:
            account = await self._get_account(session, chat_id)
            if account:
                account_id = account.id
                user_id = account.user_id

        if account_id is None or user_id is None:
            await self.send_response(
                chat_id,
                f"Your Telegram is not linked. Register at {settings.base_url}/register and link your account from the dashboard.",
            )
            return

        # Detect message type after authorization.
        message_type = MessageType.text
        file_url = None

        if "photo" in message:
            message_type = MessageType.image
            photo = message["photo"][-1]  # largest size
            file_url = await self._download_file(photo["file_id"])
            text = message.get("caption", "")
        elif "voice" in message:
            message_type = MessageType.voice
            file_url = await self._download_file(message["voice"]["file_id"])
            text = ""

        async with async_session() as session:
            initial_status = (
                MESSAGE_STATUS_PREPROCESSING
                if requires_preprocessing(message_type, text)
                else MESSAGE_STATUS_PENDING
            )
            msg = Message(
                external_account_id=account_id,
                provider="telegram",
                provider_chat_id=chat_id,
                content=text,
                message_type=message_type,
                file_url=file_url,
                status=initial_status,
            )
            session.add(msg)
            await session.commit()

        log.info(
            "message_saved",
            message_id=msg.id,
            chat_id=chat_id,
            message_type=message_type.value,
            status=initial_status,
        )

        from tasks.preprocess_message import preprocess_message
        from tasks.process_message import process_message

        if initial_status == MESSAGE_STATUS_PREPROCESSING:
            preprocess_message.delay(msg.id)
        else:
            process_message.delay(user_id)

    async def send_response(self, chat_id: str, text: str) -> None:
        await self._client.post(
            f"{self.api_url}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )

    async def _handle_start(self, chat_id: str, username: str | None, code: str) -> None:
        redis = get_redis()
        user_id = await resolve_link_code(code, redis)

        if user_id is None:
            await self.send_response(chat_id, "Invalid or expired code. Generate a new one from the dashboard.")
            return

        async with async_session() as session:
            # Check if already linked
            existing = await self._get_account(session, chat_id)
            if existing:
                await self.send_response(chat_id, "This Telegram account is already linked.")
                return

            account = ExternalAccount(
                user_id=user_id,
                provider="telegram",
                provider_user_id=chat_id,
                username=username,
            )
            session.add(account)
            await session.commit()

        log.info("account_linked", user_id=user_id, chat_id=chat_id)
        await self.send_response(chat_id, "Account linked successfully!")

    async def _download_file(self, file_id: str) -> str:
        resp = await self._client.get(f"{self.api_url}/getFile", params={"file_id": file_id})
        file_path = resp.json()["result"]["file_path"]
        filename = Path(file_path).name

        download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
        file_resp = await self._client.get(download_url)

        media_dir = Path(settings.media_dir)
        media_dir.mkdir(parents=True, exist_ok=True)

        local_path = media_dir / f"{file_id}_{filename}"
        local_path.write_bytes(file_resp.content)

        log.info("file_downloaded", file_id=file_id, path=str(local_path))
        return str(local_path.resolve())

    async def _get_account(self, session: AsyncSession, chat_id: str) -> ExternalAccount | None:
        result = await session.execute(
            select(ExternalAccount).where(
                ExternalAccount.provider == "telegram",
                ExternalAccount.provider_user_id == chat_id,
            )
        )
        return result.scalar_one_or_none()

    async def ensure_polling_mode(self) -> None:
        await self._client.post(f"{self.api_url}/deleteWebhook")

    async def start_polling(self) -> None:
        self._polling = True
        await self.ensure_polling_mode()
        log.info("polling_started")
        offset = 0

        while self._polling:
            try:
                resp = await self._client.get(
                    f"{self.api_url}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                updates = resp.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    await self.on_message(update)
            except httpx.TimeoutException:
                continue
            except Exception:
                log.exception("polling_error")
                await asyncio.sleep(1)

    def stop_polling(self) -> None:
        self._polling = False

    async def close(self) -> None:
        self.stop_polling()
        await self._client.aclose()
