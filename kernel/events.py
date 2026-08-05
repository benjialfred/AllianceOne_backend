import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


class DomainEvent:
    """
    Base class for all domain events in Alliance One.
    Every event is a typed object containing only primitive types or UUIDs.
    """

    name: str = "BaseEvent"

    def __init__(self, **kwargs: Any) -> None:
        self.event_id: str = str(uuid.uuid4())
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.payload: Dict[str, Any] = kwargs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_name": self.name,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    def __repr__(self) -> str:
        return f"<{self.name} {self.event_id}>"


class EventBus:
    """
    In-memory event bus for the Kernel.
    Later, this will publish to Redis / Celery / RabbitMQ.
    """

    _subscribers: Dict[str, List[Callable[[DomainEvent], None]]] = {}

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable[[DomainEvent], None]) -> None:
        if event_name not in cls._subscribers:
            cls._subscribers[event_name] = []
        cls._subscribers[event_name].append(handler)

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        """
        Publishes an event to all registered subscribers.
        Currently synchronous. Will be asynchronous in production.
        """
        handlers = cls._subscribers.get(event.name, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Logging will be injected here
                print(f"Error handling event {event.name}: {str(e)}")

    @classmethod
    def clear(cls) -> None:
        """For testing purposes."""
        cls._subscribers = {}
