from uuid import uuid4

import httpx
import structlog
from sqlmodel import select

from ai.agents.intake import decide_intake_action
from ai.router import route_message
from celery_app import celery
from config import settings
from db_sync import SyncSessionLocal
from models.external_account import ExternalAccount
from models.message import (
    MESSAGE_STATUS_DONE,
    MESSAGE_STATUS_ERROR,
    MESSAGE_STATUS_PENDING,
    Message,
)
from redis_client import get_sync_redis
from services.message_pipeline import build_effective_content

log = structlog.get_logger()

HISTORY_LIMIT = 8
WAIT_COUNTDOWN_SECONDS = 0.5
MAX_WAIT_ATTEMPTS = 3
LOCK_TTL_SECONDS = 120


def _send_telegram(chat_id: str, text: str) -> None:
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
    with httpx.Client(timeout=30.0) as client:
        client.post(f"{api_url}/sendMessage", json={"chat_id": chat_id, "text": text})


@celery.task(name="tasks.process_message", bind=True, max_retries=2)
def process_message(
    self,
    user_id: int,
    wait_attempt: int = 0,
    latest_seen_message_id: int | None = None,
) -> None:
    lock_key = f"message-processing-lock:{user_id}"
    lock_token = str(uuid4())
    redis = get_sync_redis()

    if not redis.set(lock_key, lock_token, nx=True, ex=LOCK_TTL_SECONDS):
        log.info("message_processing_locked", user_id=user_id)
        process_message.apply_async(
            kwargs={
                "user_id": user_id,
                "wait_attempt": wait_attempt,
                "latest_seen_message_id": latest_seen_message_id,
            },
            countdown=WAIT_COUNTDOWN_SECONDS,
        )
        return

    batch_ids: list[int] = []
    active_provider: str | None = None
    active_chat_id: str | None = None

    try:
        with SyncSessionLocal() as session:
            latest_pending = session.execute(
                select(Message)
                .join(ExternalAccount, Message.external_account_id == ExternalAccount.id)
                .where(
                    ExternalAccount.user_id == user_id,
                    Message.status == MESSAGE_STATUS_PENDING,
                )
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(1)
            ).scalars().first()
            if not latest_pending:
                log.info("no_pending_messages", user_id=user_id)
                return

            active_provider = latest_pending.provider
            active_chat_id = latest_pending.provider_chat_id

            pending_messages = session.execute(
                select(Message)
                .join(ExternalAccount, Message.external_account_id == ExternalAccount.id)
                .where(
                    ExternalAccount.user_id == user_id,
                    Message.provider == active_provider,
                    Message.provider_chat_id == active_chat_id,
                    Message.status == MESSAGE_STATUS_PENDING,
                )
                .order_by(Message.created_at.asc(), Message.id.asc())
            ).scalars().all()
            if not pending_messages:
                log.info("no_pending_batch", user_id=user_id, provider=active_provider, chat_id=active_chat_id)
                return

            effective_wait_attempt = wait_attempt
            if latest_seen_message_id != pending_messages[-1].id:
                effective_wait_attempt = 0

            pending_batch_lines: list[str] = []
            combined_parts: list[str] = []
            for index, message in enumerate(pending_messages, start=1):
                content = _message_content(message)
                if not content:
                    continue
                pending_batch_lines.append(f"Message {index} ({message.message_type.value}): {content}")
                combined_parts.append(content)

            pending_batch_text = "\n\n".join(pending_batch_lines)
            combined_user_content = "\n\n".join(combined_parts)

            recent_history = list(
                reversed(
                    session.execute(
                        select(Message)
                        .join(ExternalAccount, Message.external_account_id == ExternalAccount.id)
                        .where(
                            ExternalAccount.user_id == user_id,
                            Message.provider == active_provider,
                            Message.provider_chat_id == active_chat_id,
                            Message.status == MESSAGE_STATUS_DONE,
                        )
                        .order_by(Message.created_at.desc(), Message.id.desc())
                        .limit(HISTORY_LIMIT)
                    ).scalars().all()
                )
            )

            recent_history_lines: list[str] = []
            for message in recent_history:
                content = _message_content(message)
                if content:
                    recent_history_lines.append(f"User: {content}")
                if message.response:
                    recent_history_lines.append(f"Assistant: {message.response}")
            recent_history_text = "\n".join(recent_history_lines)

            intake_result = decide_intake_action(
                pending_batch=pending_batch_text,
                recent_history=recent_history_text,
                wait_attempt=effective_wait_attempt,
                max_wait_attempts=MAX_WAIT_ATTEMPTS,
            )

            action = intake_result.action
            question = intake_result.question
            if action == "wait" and effective_wait_attempt >= MAX_WAIT_ATTEMPTS:
                action = "ask_user"
                question = question or "Could you tell me a bit more?"

            if action == "wait":
                process_message.apply_async(
                    kwargs={
                        "user_id": user_id,
                        "wait_attempt": effective_wait_attempt + 1,
                        "latest_seen_message_id": pending_messages[-1].id,
                    },
                    countdown=WAIT_COUNTDOWN_SECONDS,
                )
                log.info(
                    "message_batch_waiting",
                    user_id=user_id,
                    chat_id=active_chat_id,
                    wait_attempt=effective_wait_attempt + 1,
                )
                return

            batch_ids = [message.id for message in pending_messages if message.id is not None]
            for message in pending_messages:
                message.error_detail = None
            session.commit()

            if action == "ask_user":
                response_text = question or "Could you tell me a bit more?"
            else:
                response_text = route_message(
                    user_id,
                    combined_user_content,
                    recent_history=recent_history_text,
                )

            for message in pending_messages[:-1]:
                message.status = MESSAGE_STATUS_DONE
                message.response = None

            last_message = pending_messages[-1]
            last_message.status = MESSAGE_STATUS_DONE
            last_message.response = response_text
            session.commit()

            if last_message.provider == "telegram":
                _send_telegram(last_message.provider_chat_id, response_text)

            log.info(
                "message_batch_processed",
                user_id=user_id,
                chat_id=active_chat_id,
                batch_size=len(pending_messages),
                action=action,
            )

            has_more_pending = (
                session.execute(
                    select(Message.id)
                    .join(ExternalAccount, Message.external_account_id == ExternalAccount.id)
                    .where(
                        ExternalAccount.user_id == user_id,
                        Message.status == MESSAGE_STATUS_PENDING,
                    )
                    .limit(1)
                ).first()
                is not None
            )
            if has_more_pending:
                process_message.delay(user_id)

    except Exception as exc:
        if batch_ids:
            with SyncSessionLocal() as session:
                failed_messages = session.execute(select(Message).where(Message.id.in_(batch_ids))).scalars().all()
                for message in failed_messages:
                    message.status = MESSAGE_STATUS_ERROR
                    message.error_detail = str(exc)[:500]
                session.commit()

        log.exception("message_processing_failed", user_id=user_id, chat_id=active_chat_id)
        raise self.retry(exc=exc, countdown=30)

    finally:
        _release_lock(redis, lock_key, lock_token)


def _message_content(message: Message) -> str:
    return build_effective_content(
        message_type=message.message_type,
        content=message.content,
        processed_content=message.processed_content,
    )


def _release_lock(redis, lock_key: str, lock_token: str) -> None:
    try:
        current_token = redis.get(lock_key)
        if current_token == lock_token:
            redis.delete(lock_key)
    except Exception:
        log.exception("message_lock_release_failed", lock_key=lock_key)
