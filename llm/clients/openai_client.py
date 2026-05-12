"""
OpenAI LLM client implementation.
"""
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponseFactory, StandardLLMResponse, StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.events import emits, EventTypes
from optorch.filters import FilterManager

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client (GPT-4, GPT-4o, etc.)
    """
    
    MODEL_PATTERNS = ["gpt-", "o1-", "text-embedding", "davinci", "curie", "babbage", "ada"]
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        tpm_limit: int = 90000
    ):
        super().__init__(model=model, tpm_limit=tpm_limit)
        self.api_key = api_key
        self.temperature = temperature
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    @emits(EventTypes.LLM)
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        self.active_requests += 1
        
        try:
            temperature = kwargs.pop('temperature', self.temperature)
            tools = kwargs.pop('tools', None)
            
            filtered_messages = FilterManager.for_target("messages", "openai").apply(messages)
            
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
            
            usage_data = response.usage
            if usage_data:
                from optorch.llm.pricing import Pricing
                usage = Usage.create(model_key, usage_data.prompt_tokens, usage_data.completion_tokens, currency=Pricing.get_currency())
            else:
                usage = None
            
            return LLMResponseFactory.create(
                content=message.content,
                tool_calls=[{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in (message.tool_calls or [])],
                usage=usage,
                raw_response=response
            )
        finally:
            self.active_requests -= 1

    @emits(EventTypes.LLM)
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """Stream response - processes OpenAI delta format"""
        self.active_requests += 1
        
        try:
            temperature = kwargs.pop('temperature', self.temperature)
            tools = kwargs.pop('tools', None)
            budget = kwargs.pop('budget', None)
            completion_type = kwargs.pop('completion_type', 'hard_stop')
            
            filtered_messages = FilterManager.for_target("messages", "openai").apply(messages)
            
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
                provider="openai",
                metadata={
                    "temperature": temperature,
                    "tools": tools is not None
                },
                budget=budget,
                completion_type=completion_type
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
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in response.choices[0].message.tool_calls
        ]
    
    def _extract_usage(self, response) -> Optional[Usage]:
        """Extract usage from OpenAI ChatCompletion response"""
        usage_data = response.usage
        if not usage_data:
            return None
        model_name = self.model or "unknown"
        model_key = f"{self.provider_prefix}/{model_name}" if self.provider_prefix else model_name
        from optorch.llm.pricing import Pricing
        return Usage.create(model_key, usage_data.prompt_tokens, usage_data.completion_tokens, currency=Pricing.get_currency())
    
    def _get_provider_name(self) -> str:
        return "openai"
