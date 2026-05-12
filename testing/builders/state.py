from typing import Dict, Any, Optional, List
from optorch.testing.mocks.state import MockStateContainer


class StateBuilder:
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
    
    def with_message(self, message: str):
        self._data["user_message"] = message
        return self
    
    def with_session_id(self, session_id: str):
        self._data["session_id"] = session_id
        return self
    
    def with_entities(self, entity_type: str, entities: List[Dict]):
        if "entities" not in self._data:
            self._data["entities"] = {}
        self._data["entities"][entity_type] = entities
        return self
    
    def with_dependencies(self, dependencies: List[Dict]):
        return self.with_entities("dependencies", dependencies)
    
    def with_response(self, response: str):
        self._data["response"] = response
        return self
    
    def with_key(self, key: str, value: Any):
        self._data[key] = value
        return self
    
    def with_error(self, error: str):
        self._data["error"] = error
        return self
    
    def build(self) -> MockStateContainer:
        return MockStateContainer(self._data.copy())
