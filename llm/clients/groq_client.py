"""Groq LLM client implementation"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponseFactory, StandardLLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.events import emits, EventTypes
from optorch.filters import FilterManager

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class GroqClient(BaseLLMClient):
    """
    Groq API client (fast inference for Llama, Mixtral, etc.)
    """
    
    MODEL_PATTERNS = ["mixtral", "llama3-", "llama-3", "gemma"]
    
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-70b-versatile",
        temperature: float = 0.7,
        tpm_limit: int = 30000  # Groq has lower TPM limits
    ):
        super().__init__(model=model, tpm_limit=tpm_limit, provider_prefix="groq")
        self.api_key = api_key
        self.temperature = temperature
        self._client = None
    
    @property
    def client(self):
        """Lazy load Groq client"""
        if self._client is None:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=self.api_key)
            except ImportError:
                raise ImportError("groq package not installed. Install with: pip install groq")
        return self._client
    
    @emits(EventTypes.LLM)
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        """
        Call Groq API.
        
        Args:
            messages: Chat messages in OpenAI-compatible format
            **kwargs: Additional Groq parameters (tools, temperature, etc.)
        """
        self.active_requests += 1
        try:
            temperature = kwargs.pop('temperature', self.temperature)
            tools = kwargs.pop('tools', None)
            
            filtered_messages = FilterManager.for_target("messages", "groq").apply(messages)
            
            params = {
                "model": self.model,
                "messages": filtered_messages,
                "temperature": temperature,
                **kwargs
            }
            
            if tools:
                params["tools"] = tools
            
            response = await self.client.chat.completions.create(**params)
            message = response.choices[0].message
            
            model_name = self.model or "unknown"
            model_key = f"{self.provider_prefix}/{model_name}" if self.provider_prefix else model_name
            
            return LLMResponseFactory.create(
                content=message.content,
                tool_calls=[{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in (message.tool_calls or [])] if message.tool_calls else None,
                usage=Usage.create(model_key, response.usage.prompt_tokens, response.usage.completion_tokens),
                raw_response=response
            )
        finally:
            self.active_requests -= 1
    
    @emits(EventTypes.LLM)
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """
        Stream Groq API response.
        
        Args:
            messages: Chat messages in OpenAI-compatible format
            **kwargs: Additional Groq parameters (tools, temperature, etc.)
        """
        self.active_requests += 1
        try:
            temperature = kwargs.pop("temperature", self.temperature)
            tools = kwargs.pop("tools", None)
            
            filtered_messages = FilterManager.for_target("messages", "groq").apply(messages)
            
            params = {
                "model": self.model,
                "messages": filtered_messages,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
                **kwargs
            }
            
            if tools:
                params["tools"] = tools
            
            stream = await self.client.chat.completions.create(**params)
            
            return StreamingLLMResponse(
                stream=stream,
                model=self.model,
                provider="groq"
            )
        finally:
            self.active_requests -= 1

    async def _build_invoke_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
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
        return await self.client.chat.completions.create(**params)
    
    async def _call_stream_api(self, params: Dict[str, Any]) -> Any:
        return await self.client.chat.completions.create(**params)
    
    def _extract_content(self, response: Any) -> str:
        return response.choices[0].message.content or ""
    
    def _extract_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        if not response.choices[0].message.tool_calls:
            return None
        return [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in response.choices[0].message.tool_calls
        ]
    
    def _extract_usage(self, response: Any) -> Optional[Usage]:
        model_name = self.model or "unknown"
        model_key = f"{self.provider_prefix}/{model_name}" if self.provider_prefix else model_name
        from optorch.llm.pricing import Pricing
        return Usage.create(model_key, response.usage.prompt_tokens, response.usage.completion_tokens, currency=Pricing.get_currency())
    
    def _get_provider_name(self) -> str:
        return "groq"
