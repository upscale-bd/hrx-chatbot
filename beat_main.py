"""Helper to remind how to start Celery beat for scheduling periodic tasks.

Usage:
    celery -A worker.celery_app beat --loglevel=info
"""

if __name__ == "__main__":
    print("Start Celery beat with: celery -A worker.celery_app beat --loglevel=info")
