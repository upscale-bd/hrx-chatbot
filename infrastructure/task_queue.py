"""
Task Queue Abstraction Layer

This module provides an abstraction for background task queueing,
decoupling business logic from the specific task queue implementation (Celery).

Benefits:
- Follows Dependency Inversion Principle (SOLID)
- Easy to test (can mock the interface)
- Flexible: can swap Celery for other queue systems
- Prevents circular dependencies
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from celery import Celery
from celery.result import AsyncResult
from uuid import UUID
from common.logger import get_logger


class TaskQueue(ABC):
    """Abstract interface for background task queueing"""

    @abstractmethod
    def send_task(
        self,
        task_name: str,
        args: tuple = None,
        kwargs: dict = None,
        countdown: int = None,
        **options
    ) -> str:
        """
        Send a task to the queue for background processing

        Args:
            task_name: Full task name (e.g., 'worker.dataset.dataset_worker.process_dataset')
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            countdown: Delay in seconds before task execution
            **options: Additional queue-specific options

        Returns:
            Task ID (string)
        """
        pass

    @abstractmethod
    def get_task_result(self, task_id: UUID) -> Optional[Any]:
        """
        Get the result of a completed task

        Args:
            task_id: Task ID returned from send_task

        Returns:
            Task result if available, None otherwise
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: UUID) -> str:
        """
        Get the current status of a task

        Args:
            task_id: Task ID returned from send_task

        Returns:
            Task status string (e.g., 'PENDING', 'SUCCESS', 'FAILURE')
        """
        pass


class CeleryTaskQueue(TaskQueue):
    """Celery implementation of the TaskQueue interface"""

    def __init__(self, celery_app: Celery):
        """
        Initialize Celery task queue

        Args:
            celery_app: Configured Celery application instance
        """
        self.celery_app = celery_app
        self.logger = get_logger("CeleryTaskQueue")

    def send_task(
        self,
        task_name: str,
        args: tuple = None,
        kwargs: dict = None,
        countdown: int = None,
        **options
    ) -> str:
        """Send a task to Celery queue"""
        try:
            task_args = args or ()
            task_kwargs = kwargs or {}

            # Build Celery options
            celery_options = {}
            if countdown is not None:
                celery_options['countdown'] = countdown

            # Merge additional options
            celery_options.update(options)

            # Send task to Celery
            result: AsyncResult = self.celery_app.send_task(
                task_name,
                args=task_args,
                kwargs=task_kwargs,
                **celery_options
            )

            self.logger.info(
                f"Task '{task_name}' queued successfully with ID: {result.id}"
            )
            return result.id

        except Exception as e:
            self.logger.error(f"Failed to queue task '{task_name}': {e}")
            raise

    def get_task_result(self, task_id: UUID) -> Optional[Any]:
        """Get Celery task result"""
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            if result.ready():
                return result.result
            return None
        except Exception as e:
            self.logger.error(f"Failed to get result for task {task_id}: {e}")
            return None

    def get_task_status(self, task_id: UUID) -> str:
        """Get Celery task status"""
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            return result.status
        except Exception as e:
            self.logger.error(f"Failed to get status for task {task_id}: {e}")
            return "UNKNOWN"


class MockTaskQueue(TaskQueue):
    """Mock implementation for testing (no actual task execution)"""

    def __init__(self):
        self.logger = get_logger("MockTaskQueue")
        self.sent_tasks: list[Dict[str, Any]] = []

    def send_task(
        self,
        task_name: str,
        args: tuple = None,
        kwargs: dict = None,
        countdown: int = None,
        **options
    ) -> str:
        """Mock task sending (stores task info without execution)"""
        task_id = f"mock-task-{len(self.sent_tasks)}"

        task_info = {
            "task_id": task_id,
            "task_name": task_name,
            "args": args or (),
            "kwargs": kwargs or {},
            "countdown": countdown,
            "options": options,
        }

        self.sent_tasks.append(task_info)

        self.logger.info(f"Mock task '{task_name}' recorded with ID: {task_id}")
        return task_id

    def get_task_result(self, task_id: UUID) -> Optional[Any]:
        """Mock result retrieval"""
        return {"status": "mock_result", "task_id": task_id}

    def get_task_status(self, task_id: UUID) -> str:
        """Mock status retrieval"""
        return "SUCCESS"

    def get_sent_tasks(self) -> list[Dict[str, Any]]:
        """Get all tasks that were sent (useful for testing)"""
        return self.sent_tasks

    def clear(self):
        """Clear task history (useful for test cleanup)"""
        self.sent_tasks.clear()


# Factory function for easy instantiation
def get_task_queue(celery_app: Optional[Celery] = None, mock: bool = False) -> TaskQueue:
    """
    Factory function to get the appropriate TaskQueue implementation

    Args:
        celery_app: Celery application instance (required if mock=False)
        mock: If True, returns MockTaskQueue for testing

    Returns:
        TaskQueue implementation
    """
    logger = get_logger("TaskQueueFactory")
    
    if mock:
        return MockTaskQueue()

    if celery_app is None:
        try:
            # Lazy import to avoid circular dependencies
            from worker.celery_app import celery_app as default_celery_app
            celery_app = default_celery_app
            logger.info("Successfully loaded default celery_app")
        except ImportError as e:
            logger.error(f"Failed to import celery_app: {e}")
            logger.warning("Falling back to MockTaskQueue due to import error")
            # Fallback to mock queue if celery_app cannot be imported
            # This prevents the app from crashing during startup
            return MockTaskQueue()
        except Exception as e:
            logger.error(f"Unexpected error loading celery_app: {e}")
            logger.warning("Falling back to MockTaskQueue due to unexpected error")
            return MockTaskQueue()

    return CeleryTaskQueue(celery_app)
