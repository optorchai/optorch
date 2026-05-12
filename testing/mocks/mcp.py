from typing import Dict, Any, List, Optional


class MockMCPClient:
    
    def __init__(self):
        self.tool_calls: List[Dict[str, Any]] = []
        self.tool_responses: Dict[str, List[Any]] = {}
    
    def add_tool_response(self, tool_name: str, response: Any):
        if tool_name not in self.tool_responses:
            self.tool_responses[tool_name] = []
        self.tool_responses[tool_name].append(response)
        return self
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        self.tool_calls.append({
            "tool_name": tool_name,
            "arguments": arguments
        })
        
        if tool_name not in self.tool_responses or not self.tool_responses[tool_name]:
            return {"status": "success", "result": f"Mock response for {tool_name}"}
        
        return self.tool_responses[tool_name].pop(0)
    
    def assert_tool_called(self, tool_name: str, times: Optional[int] = None):
        calls = [c for c in self.tool_calls if c["tool_name"] == tool_name]
        actual = len(calls)
        
        if times is not None:
            assert actual == times, f"Expected {times} calls to '{tool_name}', got {actual}"
        else:
            assert actual > 0, f"Expected at least one call to '{tool_name}'"
    
    def assert_tool_called_with(self, tool_name: str, **kwargs):
        calls = [c for c in self.tool_calls if c["tool_name"] == tool_name]
        assert len(calls) > 0, f"No calls to '{tool_name}'"
        
        last_call = calls[-1]
        for key, value in kwargs.items():
            assert key in last_call["arguments"], f"Argument '{key}' not in call"
            assert last_call["arguments"][key] == value, f"Expected {value}, got {last_call['arguments'][key]}"
