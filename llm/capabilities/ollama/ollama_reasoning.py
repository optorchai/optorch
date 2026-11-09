from typing import Any, ClassVar, Dict, Optional
from optorch.llm.capabilities.capability import Capability

class OllamaReasoning(Capability):    
    provider: ClassVar[str] = "ollama"
    name: ClassVar[str] = "reasoning"
    accumulation_key: ClassVar[str] = "reasoning"
    
    def contribute(self, model: str) -> Optional[Dict[str, Any]]:
        return {"think": True}
    
    def extract(self, chunk: Any) -> Optional[Dict[str, Any]]:
        if isinstance(chunk, dict):
            message = chunk.get("message")
        else:
            message = getattr(chunk, "message", None)

        if message is None:
            return None
        
        if isinstance(message, dict):
            thinking = message.get("thinking")
        else:
            thinking = getattr(message, "thinking", None)

        if not thinking:
            return None
        
        return {"type": self.event_type, "content": thinking}
