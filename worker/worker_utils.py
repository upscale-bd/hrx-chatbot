"""
Worker utilities for shared async operations
"""

import asyncio
from typing import Callable, Any
from common.logger import get_logger

logger = get_logger("worker_utils")

# Global reference to the main worker loop
_worker_loop = None


def set_worker_loop(loop: asyncio.AbstractEventLoop):
    """Set the shared worker event loop (called from worker_main)."""
    global _worker_loop
    _worker_loop = loop


def get_worker_loop() -> asyncio.AbstractEventLoop:
    """Get the shared worker event loop."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        raise RuntimeError("Worker event loop not initialized. Call set_worker_loop() first.")
    return _worker_loop


def run_async(coro: Callable[[], Any]) -> Any:
    """
    Run async coroutine using the shared worker event loop.
    This is the standard way to run async code in Celery tasks.
    """
    try:
        loop = get_worker_loop()
        return loop.run_until_complete(coro())
    except Exception as e:
        logger.error(f"Error running async task: {e}")
        raise
