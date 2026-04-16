"""Worker main helper.

Usage:
    celery -A worker.celery_app worker --loglevel=info
"""

if __name__ == "__main__":
    print("Start a Celery worker with: celery -A worker.celery_app worker --loglevel=info")
