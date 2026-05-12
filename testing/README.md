# Testing Optorch

Optorch utilities for writing clean, maintainable tests.

## Quick Start

```python
from optorch.testing import (
    MockLLMProvider,
    StateBuilder,
    EventCapture,
    assert_event_emitted,
    assert_state_contains
)

def test_node_execution():
    mock_llm = MockLLMProvider()
    mock_llm.add_response(content="Test response")
    
    state = StateBuilder().with_message("test").build()
    
    with EventCapture() as capture:
        # test your code
        pass
    
    assert_event_emitted("node.complete", capture)
    assert_state_contains(state, "result")
```

## Mocks

- `MockLLMProvider` - fake LLM with queued responses
- `MockStateContainer` - state tracking access/writes
- `EventCapture` - capture emitted events
- `MockNode` - fake node execution
- `MockMCPClient` - fake tool calls

## Builders

- `StateBuilder()` - fluent state construction
- `MessageBuilder()` - build message arrays
- `ConversationBuilder()` - build multi-turn conversations

## Assertions

- `assert_event_emitted(type, capture)`
- `assert_state_contains(state, key, value)`
- `assert_llm_called(mock, times=1)`

## Pytest Fixtures

Add to `conftest.py`:

```python
pytest_plugins = ["optorch.testing.fixtures.pytest"]
```

Then use in tests:

```python
def test_something(mock_llm, event_capture, state_builder):
    # fixtures auto-injected
    pass
```
