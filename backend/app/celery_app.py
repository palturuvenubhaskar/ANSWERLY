"""Celery application for Answerly background job processing."""

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MAX_CONCURRENCY = int(os.getenv("MAX_WORKER_CONCURRENCY", "4"))

celery_app = Celery(
    "answerly",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=MAX_CONCURRENCY,
    task_reject_on_worker_lost=True,
    task_time_limit=int(os.getenv("MODEL_TIMEOUT_SECONDS", "120")) * 4,
    task_soft_time_limit=int(os.getenv("MODEL_TIMEOUT_SECONDS", "120")) * 3,
    task_default_rate_limit=f"{MAX_CONCURRENCY}/s",
    broker_connection_retry_on_startup=True,
    task_always_eager=os.getenv("CELERY_ALWAYS_EAGER", "false").lower() in ("true", "1", "yes"),
)

celery_app.autodiscover_tasks(["backend.app"])
