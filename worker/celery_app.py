from celery import Celery
from config.config import settings
from worker.beat_schedule import beat_schedule
from common.logger import get_logger

logger = get_logger("celery_app")

logger.info("[celery_app] Initializing Celery app")
logger.info(f"[celery_app] Broker: {settings.CELERY_BROKER_URL}")
logger.info(f"[celery_app] Backend: {settings.CELERY_RESULT_BACKEND}")

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "worker.report_worker",
    ]
)

celery_app.conf.beat_schedule = beat_schedule
celery_app.conf.timezone = "UTC"
logger.info(f"[celery_app] Celery app configured | timezone=UTC | tasks={['worker.report_worker']}")
