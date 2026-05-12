from optorch.testing.mocks.events import EventCapture


def assert_event_emitted(event_type: str, capture: EventCapture, times: int | None = None):
    capture.assert_emitted(event_type, times)


def assert_event_not_emitted(event_type: str, capture: EventCapture):
    capture.assert_not_emitted(event_type)


def assert_event_data(event_type: str, capture: EventCapture, **kwargs):
    for key, value in kwargs.items():
        capture.assert_event_data(event_type, key, value)
