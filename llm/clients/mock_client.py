"""
Mock LLM client for testing - behaves exactly like real clients, no cost
Simple implementation that provides the interface needed for testing
"""
import asyncio
from typing import List, Dict, Any, TYPE_CHECKING
from optorch.llm.responses import StandardLLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.events import emits, EventTypes

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class MockClient:
    """
    Mock LLM client that behaves like real OpenAI/Groq/Ollama clients
    Returns realistic responses without API costs
    
    Simple implementation for testing - provides the basic interface
    """
    
    def __init__(
        self,
        model: str = "mock-gpt-4o", 
        temperature: float = 0.7,
        tpm_limit: int = 90000,
        response_delay: float = 0.1  # simulate network delay
    ):
        self.model = model
        self.temperature = temperature
        self.tpm_limit = tpm_limit
        self.response_delay = response_delay
        self.call_count = 0
        self.active_requests = 0
        
    
    def _get_response(self, messages: List[Dict[str, Any]]) -> str:
        """Return simple lorem ipsum response"""
        return """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium."""

    @emits(EventTypes.LLM)
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        """Mock invoke with realistic behavior"""
        self.active_requests += 1
        self.call_count += 1
        
        try:
            # Simulate network delay
            await asyncio.sleep(self.response_delay)
            
            # Get response
            content = self._get_response(messages)
            
            # Simulate realistic token usage
            prompt_tokens = sum(len(msg.get("content", "").split()) for msg in messages) * 1.3
            completion_tokens = len(content.split()) * 1.2
            
            return StandardLLMResponse(
                _content=content,
                _usage=Usage(
                    input_tokens=int(prompt_tokens),
                    output_tokens=int(completion_tokens), 
                    total_tokens=int(prompt_tokens + completion_tokens),
                    currency="USD"
                ),
                _metadata={
                    "model": self.model,
                    "provider": "mock",
                    "mock": True,
                    "call_count": self.call_count,
                    "temperature": self.temperature
                }
            )
        
        finally:
            self.active_requests -= 1

    @emits(EventTypes.LLM)  
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """Mock streaming with realistic chunks"""
        async def _stream_chunks():
            self.active_requests += 1
            self.call_count += 1
            
            try:
                # Get response and chunk it
                content = self._get_response(messages)
                words = content.split()
                
                # Simulate streaming delay
                await asyncio.sleep(self.response_delay * 0.1)
                
                for i, word in enumerate(words):
                    chunk = {
                        "choices": [{
                            "delta": {"content": word + " "},
                            "index": 0,
                            "finish_reason": "stop" if i == len(words) - 1 else None
                        }],
                        "model": self.model,
                        "id": f"mock_chunk_{self.call_count}_{i}"
                    }
                    
                    # Add usage on last chunk
                    if i == len(words) - 1:
                        chunk["usage"] = {
                            "prompt_tokens": sum(len(msg.get("content", "").split()) for msg in messages),
                            "completion_tokens": len(words),
                            "total_tokens": sum(len(msg.get("content", "").split()) for msg in messages) + len(words)
                        }
                    
                    yield chunk
                    await asyncio.sleep(0.01)  # Realistic streaming delay
                    
            finally:
                self.active_requests -= 1
        
        return StreamingLLMResponse(
            stream=_stream_chunks(),
            model=self.model,
            provider="mock",
            pre_processed=False
        )
    
    def __repr__(self):
        return f"MockClient(model={self.model}, calls={self.call_count})"