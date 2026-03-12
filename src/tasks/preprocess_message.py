import structlog

from celery_app import celery
from db_sync import SyncSessionLocal
from models.external_account import ExternalAccount
from models.message import (
    MESSAGE_STATUS_DONE,
    MESSAGE_STATUS_ERROR,
    MESSAGE_STATUS_PENDING,
    Message,
    MessageType,
)
from services.media_preprocessing import scrape_urls, transcribe_media
from tasks.process_message import process_message

log = structlog.get_logger()


@celery.task(name="tasks.preprocess_message", bind=True, max_retries=2)
def preprocess_message(self, message_id: int) -> None:
    user_id: int | None = None

    try:
        with SyncSessionLocal() as session:
            message = session.get(Message, message_id)
            if not message:
                log.error("message_not_found_for_preprocessing", message_id=message_id)
                return

            if message.status == MESSAGE_STATUS_DONE:
                log.info("message_already_done", message_id=message_id)
                return

            account = session.get(ExternalAccount, message.external_account_id)
            if not account:
                raise ValueError(f"No external account for message {message_id}")
            user_id = account.user_id

            log.info("preprocessing_message", message_id=message_id, message_type=message.message_type.value)

            if message.message_type == MessageType.text:
                processed_content = scrape_urls(message.content)
            else:
                if not message.file_url:
                    raise ValueError(f"No file_url for media message {message_id}")
                processed_content = transcribe_media(message.message_type, message.file_url)

            if not processed_content.strip():
                raise ValueError(f"Preprocessing produced no content for message {message_id}")

            message.processed_content = processed_content
            message.status = MESSAGE_STATUS_PENDING
            message.error_detail = None
            session.commit()

        process_message.delay(user_id)
        log.info("message_preprocessed", message_id=message_id, user_id=user_id)

    except Exception as exc:
        with SyncSessionLocal() as session:
            message = session.get(Message, message_id)
            if message:
                message.status = MESSAGE_STATUS_ERROR
                message.error_detail = str(exc)[:500]
                session.commit()

        log.exception("message_preprocessing_failed", message_id=message_id)
        raise self.retry(exc=exc, countdown=30)
