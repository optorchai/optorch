from optorch.testing.mocks.llm import MockLLMProvider


def assert_llm_called(mock: MockLLMProvider, times: int | None = None):
    mock.assert_called(times)


def assert_llm_called_with_model(mock: MockLLMProvider, model: str):
    mock.assert_called_with_model(model)


def assert_llm_message_contains(mock: MockLLMProvider, text: str):
    mock.assert_last_call_contains(text)


def assert_token_count(mock: MockLLMProvider, expected_prompt: int | None = None, expected_completion: int | None = None):
    if not mock.calls:
        raise AssertionError("No LLM calls made")
    
    # would need response tracking - placeholder for now
    pass
