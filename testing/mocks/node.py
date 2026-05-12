from typing import Dict, Any, Optional, List
from optorch.nodes.base_node import BaseNode


class MockNode(BaseNode):
    
    def __init__(self, name: str = "mock_node"):
        self.name = name
        self.execute_calls: List[Dict[str, Any]] = []
        self.return_value: Optional[Dict[str, Any]] = None
        self.should_raise: Optional[Exception] = None
    
    async def execute(self, state) -> Dict[str, Any]:

        state_data = {}
        if hasattr(state, '_data'):
            state_data = dict(getattr(state, '_data', {}))
        elif hasattr(state, 'to_dict'):
            state_data = state.to_dict()
        
        self.execute_calls.append({"state": state_data})
        
        if self.should_raise:
            raise self.should_raise
        
        return self.return_value or {"status": "success", "node": self.name}
    
    def set_return_value(self, value: Dict[str, Any]):
        self.return_value = value
        return self
    
    def set_raises(self, exception: Exception):
        self.should_raise = exception
        return self
    
    def assert_executed(self, times: Optional[int] = None):
        actual = len(self.execute_calls)
        if times is not None:
            assert actual == times, f"Expected {times} executions, got {actual}"
        else:
            assert actual > 0, f"Expected at least one execution"
