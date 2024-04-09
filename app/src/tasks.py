import logging

from celery import Celery

from src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app: Celery = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks", "src.chat.bot_ai", "src.annotations.background_tasks"],
)


@celery_app.task
def your_task():
    try:
        logger.info("Running every hour task...")
    except Exception as e:
        logger.error(f"Error in hourly task: {e}")

    return {"status": "OK"}


# Schedule the task to run every minute
# celery_app.conf.beat_schedule = {
#     "every-minute-task": {
#         "task": "src.tasks.download_users_from_db",
#         "schedule": crontab(minute="*/1"),
#     },
# }

# Start the Celery Beat scheduler
celery_app.conf.worker_redirect_stdouts = False
celery_app.conf.task_routes = {"tasks.*": {"queue": "celery"}}
celery_app.conf.update(
    result_expires=3600,
)
