from kernel.events import DomainEvent, EventBus


class MockUserCreatedEvent(DomainEvent):
    name = "UserCreated"


def test_event_bus_publish_and_subscribe() -> None:
    EventBus.clear()

    received_events = []

    def handle_event(event: DomainEvent) -> None:
        received_events.append(event)

    EventBus.subscribe("UserCreated", handle_event)

    event = MockUserCreatedEvent(user_id="12345", email="test@alliance.com")
    EventBus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].payload["email"] == "test@alliance.com"
    assert received_events[0].event_id is not None
