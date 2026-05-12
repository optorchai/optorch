import logging
from optorch.logging import get_logger
from typing import Dict, Any
from .base import BaseListener


class ConsoleListener(BaseListener):
    def __init__(self, level: int = logging.INFO) -> None:
        self.logger = get_logger("Events")
        self.logger.setLevel(level)
    
    def on_event(self, event: Dict[str, Any]):
        event_type = event.get("type", "unknown")
        
        if event_type.startswith("llm."):
            self._handle_llm(event)
        elif event_type.startswith("node."):
            self._handle_node(event)
        elif event_type.startswith("tool."):
            self._handle_tool(event)
        elif event_type.startswith("history."):
            self._handle_history(event)
    
    def _handle_llm(self, event: Dict[str, Any]):
        if event["type"] == "llm.start":
            self.logger.debug(f"LLM call: {event.get('model')}")
        elif event["type"] == "llm.complete":
            tokens = event.get("tokens", 0)
            duration = event.get("duration_ms", 0)
            self.logger.debug(f"LLM response: {tokens} tokens in {duration}ms")
    
    def _handle_node(self, event: Dict[str, Any]):
        if event["type"] == "node.start":
            self.logger.info(f"Node: {event.get('node')}")
        elif event["type"] == "node.complete":
            duration = event.get("duration_ms", 0)
            self.logger.debug(f"Node completed in {duration}ms")
    
    def _handle_tool(self, event: Dict[str, Any]):
        if event["type"] == "tool.start":
            tool_name = event.get("args", {}).get("tool_name", "unknown")
            self.logger.debug(f"Tool: {tool_name}")
        elif event["type"] == "tool.complete":
            duration = event.get("duration_ms", 0)
            self.logger.debug(f"Tool completed in {duration}ms")
    
    def _handle_history(self, event: Dict[str, Any]):
        if event["type"] == "history.complete":
            result = event.get("result")
            if isinstance(result, list):
                count = len(result)
                duration = event.get("duration_ms", 0)
                self.logger.info(f"History loaded: {count} messages in {duration}ms")
