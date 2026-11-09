from typing import Any, ClassVar, Dict, Optional
from optorch.llm.capabilities.capability import Capability

class OpenAIReasoning(Capability):    
    provider: ClassVar[str] = "openai"
    name: ClassVar[str] = "reasoning"
    accumulation_key: ClassVar[str] = "reasoning"
    
    DEFAULT_EFFORT: ClassVar[str] = "medium"
    DEFAULT_SUMMARY: ClassVar[str] = "detailed"

    def __init__(self, event_type: str, effort: Optional[str] = None, summary: Optional[str] = None) -> None:
        super().__init__(event_type)
        self.effort = effort or self.DEFAULT_EFFORT
        self.summary = summary or self.DEFAULT_SUMMARY

    def contribute(self, model: str) -> Optional[Dict[str, Any]]:
        return {"reasoning": {"effort": self.effort, "summary": self.summary}}

    def extract(self, chunk: Any) -> Optional[Dict[str, Any]]:
        if getattr(chunk, "type", None) == "response.output_item.added":
            item = getattr(chunk, "item", None)

            if item and getattr(item, "type", None) == "reasoning":
                return {"type": self.event_type, "content": "", "data": {"status": "in_progress"}}
            
            return None

        if getattr(chunk, "type", None) == "response.reasoning_summary_text.delta":
            delta = getattr(chunk, "delta", None)

            if delta:
                return {"type": self.event_type, "content": delta}
            
            return None

        if getattr(chunk, "type", None) == "response.completed":
            response = getattr(chunk, "response", None)
            usage = getattr(response, "usage", None) if response else None

            if usage:
                reasoning_tokens = getattr(usage, "output_tokens_details", None)

                if reasoning_tokens:
                    tokens = getattr(reasoning_tokens, "reasoning_tokens", None)

                    if tokens:
                        return {"type": self.event_type, "data": {"reasoning_tokens": tokens}}
                    
            return None

        return None
