"""simple cost projector - char/4 heuristic"""

from decimal import Decimal
from typing import List, Dict, Any

from optorch.llm.projections.base import BaseCostProjector
from optorch.llm.projections.config import CostProjectionConfig
from optorch.llm.pricing import Pricing


class SimpleCostProjector(BaseCostProjector):
    """simple token projection - 1 token per 4 chars"""
    
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        # extract cost_projection config if nested, fall back to full config, or use empty dict
        projection_config_dict = (config or {}).get("cost_projection", config or {})
        self._projection_config = CostProjectionConfig(**projection_config_dict)
    
    def estimate_input(self, messages: List[Dict[str, Any]]) -> int:
        """count tokens in message list"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self._estimate_tokens(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if "text" in item:
                            total += self._estimate_tokens(item["text"])
                        elif "image_url" in item:
                            total += 85
            
            # tool calls
            if "tool_calls" in msg:
                tool_calls = msg["tool_calls"]
                if isinstance(tool_calls, list):
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn = tc.get("function", {})
                            total += self._estimate_tokens(fn.get("name", ""))
                            total += self._estimate_tokens(fn.get("arguments", ""))
            
            # role overhead
            total += 4
        
        return total
    
    def estimate_output(self, model: str) -> int:
        """estimate from config or model defaults"""
        max_tokens = self._config.get("max_tokens")
        if max_tokens:
            return max_tokens
        
        for pattern, tokens in self._projection_config.default_output_tokens.items():
            if pattern in model:
                return tokens
        
        return self._projection_config.fallback_output_tokens
    
    def predict_cost(self, model: str, messages: List[Dict[str, Any]]) -> Decimal:
        """predict total cost using actual history when available
        
        Uses last assistant response length as baseline for prediction.
        Falls back to adaptive estimation if no history available.
        """
        input_tokens = self.estimate_input(messages)
        
        max_tokens = self._config.get("max_tokens")
        if max_tokens:
            output_tokens = max_tokens
        else:
            # look at actual last response length for better accuracy
            last_assistant_msg = None
            for msg in reversed(messages):
                if msg.get("role") == "assistant":
                    last_assistant_msg = msg.get("content", "")
                    break
            
            if last_assistant_msg:
                # use actual previous response length as baseline
                # most responses are similar length to previous turn
                baseline_tokens = self._estimate_tokens(last_assistant_msg)
                output_tokens = max(10, min(150, baseline_tokens))
            else:
                # fallback: adaptive based on input (first message in conversation)
                output_tokens = max(10, min(80, int(input_tokens * 0.2)))
        
        return self.calculate_cost(model, input_tokens, output_tokens)
    
    def calculate_cost(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> Decimal:
        """calculate using pricing module"""
        return Pricing.total_cost(model, input_tokens, output_tokens)
    
    def _estimate_tokens(self, text: str) -> int:
        """rough token estimate"""
        if not text:
            return 0
        return max(1, len(text) // 4)
