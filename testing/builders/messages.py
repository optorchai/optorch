from typing import List, Dict, Any, Optional


class MessageBuilder:
    
    def __init__(self):
        self._messages: List[Dict[str, Any]] = []
    
    def system(self, content: str):
        self._messages.append({"role": "system", "content": content})
        return self
    
    def user(self, content: str):
        self._messages.append({"role": "user", "content": content})
        return self
    
    def assistant(self, content: str, tool_calls: Optional[List[Dict]] = None):
        message: Dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self._messages.append(message)
        return self
    
    def tool(self, tool_call_id: str, content: str, name: str):
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
            "name": name
        })
        return self
    
    def add_message(self, role: str, content: str, **kwargs):
        message = {"role": role, "content": content, **kwargs}
        self._messages.append(message)
        return self
    
    def build(self) -> List[Dict[str, Any]]:
        return self._messages.copy()


class ConversationBuilder:
    
    def __init__(self):
        self._turns: List[tuple[str, str]] = []
    
    def turn(self, user: str, assistant: str):
        self._turns.append((user, assistant))
        return self
    
    def build(self) -> List[Dict[str, Any]]:
        messages = []
        for user_msg, assistant_msg in self._turns:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        return messages
