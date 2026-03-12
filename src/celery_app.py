from celery import Celery
from kombu import Queue

from config import settings

celery = Celery("pensabot", broker=settings.celery_broker_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="message",
    task_queues=(
        Queue("message"),
        Queue("preprocessing"),
    ),
    task_routes={
        "tasks.process_message": {"queue": "message"},
        "tasks.preprocess_message": {"queue": "preprocessing"},
    },
)
celery.conf.include = ["tasks.process_message", "tasks.preprocess_message"]
