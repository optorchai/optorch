"""Test data factories"""

from decimal import Decimal
from typing import Dict, Any, List

from optorch.llm.responses.standard_response import StandardLLMResponse
from optorch.state.state import State


class ResponseFactory:
    """Creates test responses"""
    
    @staticmethod
    def standard(
        content: str = "test response",
        usage_tokens: int = 100,
        cost: Decimal = Decimal("0.01")
    ) -> StandardLLMResponse:
        """Create standard response"""
        return StandardLLMResponse(
            _content=content,
            _raw_response={"model": "test-model", "usage": {
                "input_tokens": usage_tokens // 2,
                "output_tokens": usage_tokens // 2,
                "total_tokens": usage_tokens,
                "cost": float(cost)
            }}
        )
    
    @staticmethod
    def with_tools(
        tool_calls: List[Dict[str, Any]]
    ) -> StandardLLMResponse:
        """Create response with tool calls"""
        return StandardLLMResponse(
            _content="",
            _tool_calls=tool_calls,
            _raw_response={"model": "test-model"}
        )


class StateFactory:
    """Creates test states"""
    
    @staticmethod
    def with_messages(messages: List[Dict[str, str]]) -> State:
        """Create state with messages"""
        state = State()
        for msg in messages:
            state.add_message(msg["role"], msg["content"])
        return state
    
    @staticmethod
    def with_data(**data) -> State:
        """Create state with arbitrary data"""
        state = State()
        for key, value in data.items():
            state[key] = value
        return state