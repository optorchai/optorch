from optorch.testing.mocks.state import MockStateContainer


def assert_state_contains(state: MockStateContainer, key: str, value=None):
    assert key in state, f"Key '{key}' not in state"
    if value is not None:
        actual = state[key]
        assert actual == value, f"Expected {value}, got {actual}"


def assert_state_equals(state: MockStateContainer, expected: dict):
    for key, value in expected.items():
        assert_state_contains(state, key, value)


def assert_state_key_accessed(state: MockStateContainer, key: str):
    state.assert_key_accessed(key)


def assert_state_key_written(state: MockStateContainer, key: str, value=None):
    state.assert_key_written(key, value)
