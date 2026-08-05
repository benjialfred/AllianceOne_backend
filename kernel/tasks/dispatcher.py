from abc import ABC, abstractmethod
from typing import Any, Dict


class TaskDispatcher(ABC):
    """
    Abstract interface for background task processing in Alliance OS.
    This ensures the Kernel and Core never depend directly on Celery or any specific queue.
    """

    @abstractmethod
    def dispatch(self, task_name: str, payload: Dict[str, Any]) -> str:
        """
        Dispatches a task immediately to the background queue.
        Returns a task_id.
        """
        pass

    @abstractmethod
    def schedule(self, task_name: str, payload: Dict[str, Any], eta: Any) -> str:
        """
        Schedules a task to run at a specific time (eta).
        Returns a task_id.
        """
        pass

    @abstractmethod
    def cancel(self, task_id: str) -> bool:
        """
        Attempts to cancel a queued or running task.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def retry(self, task_id: str, delay: int = 60) -> str:
        """
        Retries a failed task after a specified delay (in seconds).
        Returns a new task_id or the same if applicable.
        """
        pass


class DefaultTaskDispatcher(TaskDispatcher):
    """
    Default implementation of TaskDispatcher.
    In a real environment, this delegates to Celery.
    Here it serves as the abstraction layer hook.
    """
    def dispatch(self, task_name: str, payload: Dict[str, Any]) -> str:
        print(f"[TaskDispatcher] Dispatching {task_name} asynchronously.")
        # E.g. return celery_app.send_task(task_name, kwargs=payload).id
        return "mock_task_id"

    def schedule(self, task_name: str, payload: Dict[str, Any], eta: Any) -> str:
        print(f"[TaskDispatcher] Scheduling {task_name} for {eta}.")
        return "mock_scheduled_task_id"

    def cancel(self, task_id: str) -> bool:
        print(f"[TaskDispatcher] Cancelling task {task_id}.")
        return True

    def retry(self, task_id: str, delay: int = 60) -> str:
        print(f"[TaskDispatcher] Retrying task {task_id} in {delay}s.")
        return "mock_retried_task_id"
