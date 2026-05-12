from typing import List, Dict, Any, Optional
from decimal import Decimal
from optorch.llm.responses.standard_response import StandardLLMResponse


class MockLLMProvider:
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.responses: List[Dict[str, Any]] = []
        self.response_index = 0
    
    def add_response(
        self,
        content: str = "Mock response",
        tool_calls: Optional[List[Dict]] = None,
        usage: Optional[Dict[str, int]] = None,
        model: str = "mock-model",
        cost: float = 0.0
    ):
        self.responses.append({
            "content": content,
            "tool_calls": tool_calls or [],
            "usage": usage or {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "model": model,
            "cost": cost
        })
        return self
    
    def add_tool_call_response(self, tool_name: str, arguments: Dict[str, Any], content: str = ""):
        return self.add_response(
            content=content,
            tool_calls=[{
                "id": f"call_{tool_name}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }]
        )
    
    async def call(
        self,
        messages: List[Dict],
        model: str = "mock-model",
        tools: Optional[List] = None,
        **kwargs
    ) -> StandardLLMResponse:
        self.calls.append({
            "messages": messages,
            "model": model,
            "tools": tools,
            "kwargs": kwargs
        })
        
        if self.response_index >= len(self.responses):
            raise RuntimeError(f"No more mock responses (called {self.response_index + 1} times)")
        
        response_data = self.responses[self.response_index]
        self.response_index += 1
        
        return StandardLLMResponse(
            _content=response_data["content"],
            _tool_calls=response_data["tool_calls"],
            _usage=response_data["usage"],
            _raw_response={"model": response_data["model"], "cost": response_data["cost"]}
        )
    
    def reset(self):
        self.calls.clear()
        self.responses.clear()
        self.response_index = 0
    
    def assert_called(self, times: Optional[int] = None):
        if times is not None:
            actual = len(self.calls)
            assert actual == times, f"Expected {times} LLM calls, got {actual}"
        else:
            assert len(self.calls) > 0, "Expected at least one LLM call"
    
    def assert_called_with_model(self, model: str):
        models = [call["model"] for call in self.calls]
        assert model in models, f"Model {model} not found in calls: {models}"
    
    def assert_last_call_contains(self, text: str):
        assert len(self.calls) > 0, "No LLM calls made"
        last_messages = self.calls[-1]["messages"]
        all_content = " ".join([m.get("content", "") for m in last_messages])
        assert text in all_content, f"'{text}' not found in last call messages"
    
    def get_call(self, index: int = -1) -> Dict[str, Any]:
        return self.calls[index]
