"""
Ollama LLM client implementation.
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponseFactory, StandardLLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.events import emits, EventTypes
from optorch.filters import FilterManager

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext

class OllamaClient(BaseLLMClient):
    """
    Ollama local LLM client (Llama, Qwen, Mistral, etc.)
    """
    
    MODEL_PATTERNS = ["llama", "mistral", "phi", "qwen", "codellama", "neural", "orca", "vicuna"]
    
    def __init__(
        self,
        model: str = "qwen2.5:72b",
        host: str = "http://localhost:11434",
        temperature: float = 0.7,
        tpm_limit: int = 999999  # No limit for on-prem models
    ):
        super().__init__(model=model, tpm_limit=tpm_limit)
        self.host = host
        self.temperature = temperature
        self._client = None
    
    @property
    def client(self):
        """Lazy load Ollama client"""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.AsyncClient(host=self.host)
            except ImportError:
                raise ImportError("ollama package not installed. Install with: pip install ollama")
        return self._client
    
    @emits(EventTypes.LLM)
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        """
        Call Ollama API.
        
        Args:
            messages: Chat messages in OpenAI-compatible format
            **kwargs: Additional Ollama parameters (tools, temperature, etc.)
        """
        self.active_requests += 1
        try:
            temperature = kwargs.pop('temperature', self.temperature)
            tools = kwargs.pop('tools', None)
            
            filtered_messages = FilterManager.for_target("messages", "ollama").apply(messages)
            
            params = {
                "model": self.model,
                "messages": filtered_messages,
                "options": {
                    "temperature": temperature
                },
                **kwargs
            }
            
            if tools:
                params["tools"] = tools
            
            response = await self.client.chat(**params)
            message = response.get('message', {})
            
            return LLMResponseFactory.create(
                content=message.get('content'),
                tool_calls=message.get('tool_calls'),
                usage=Usage(
                    input_tokens=response.get('prompt_eval_count', 0),
                    output_tokens=response.get('eval_count', 0),
                    total_tokens=response.get('prompt_eval_count', 0) + response.get('eval_count', 0),
                    cost=0.0,
                    currency="USD"
                ),
                raw_response=response
            )
        finally:
            self.active_requests -= 1
    
    @emits(EventTypes.LLM)
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """
        Stream Ollama API response.
        
        Args:
            messages: Chat messages in OpenAI-compatible format
            **kwargs: Additional Ollama parameters (tools, temperature, etc.)
        """
        self.active_requests += 1
        try:
            temperature = kwargs.pop("temperature", self.temperature)
            tools = kwargs.pop("tools", None)
            
            filtered_messages = FilterManager.for_target("messages", "ollama").apply(messages)
            
            params = {
                "model": self.model,
                "messages": filtered_messages,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True}
            }
            
            if tools:
                params["tools"] = tools
            
            stream = self.client.chat(**params)
            
            return StreamingLLMResponse(
                stream=stream,
                model=self.model,
                provider="ollama"
            )
        finally:
            self.active_requests -= 1

    async def _build_invoke_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            **kwargs
        }
        if tools:
            params["tools"] = tools
        return params
    
    async def _build_stream_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs
        }
        if tools:
            params["tools"] = tools
        return params
    
    async def _call_api(self, params: Dict[str, Any]) -> Any:
        return await self.client.chat(**params)
    
    async def _call_stream_api(self, params: Dict[str, Any]) -> Any:
        return await self.client.chat(**params)
    
    def _extract_content(self, response: Any) -> str:
        return response.get('message', {}).get('content', '')
    
    def _extract_tool_calls(self, response) -> Optional[List[Dict[str, Any]]]:
        message = response.get('message', {})
        return message.get('tool_calls')
    
    def _extract_usage(self, response) -> Optional[Usage]:
        return Usage(
            input_tokens=response.get('prompt_eval_count', 0),
            output_tokens=response.get('eval_count', 0),
            total_tokens=response.get('prompt_eval_count', 0) + response.get('eval_count', 0),
            cost=0.0,
            currency="USD"
        )
    
    def _get_provider_name(self) -> str:
        return "ollama"
