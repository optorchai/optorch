import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from anthropic import AsyncAnthropic
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponseFactory, StandardLLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.events import emits, EventTypes
from optorch.filters import FilterManager

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext

_DEFAULT_MAX_TOKENS = 4096


class AnthropicClient(BaseLLMClient):
    MODEL_PATTERNS = ["claude-"]

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        tpm_limit: int = 40000,
    ):
        super().__init__(model=model, tpm_limit=tpm_limit, provider_prefix="anthropic")
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client: Optional[AsyncAnthropic] = None

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    @staticmethod
    def _split_system(messages: List[Dict[str, Any]]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        system: Optional[str] = None
        rest: List[Dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                rest.append(msg)
        return system, rest

    @staticmethod
    def _convert_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "tool":
                converted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content or "",
                    }],
                })
                continue

            if role == "assistant" and msg.get("tool_calls"):
                blocks: List[Dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in msg["tool_calls"]:
                    func = tc.get("function", {})
                    raw_input = func.get("arguments", "{}")
                    try:
                        parsed_input = json.loads(raw_input) if isinstance(raw_input, str) else raw_input
                    except json.JSONDecodeError:
                        parsed_input = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": parsed_input,
                    })
                converted.append({"role": "assistant", "content": blocks})
                continue

            converted.append({"role": role, "content": content})

        return converted

    @staticmethod
    def _convert_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "name": (func := t.get("function", {})).get("name", ""),
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            }
            for t in tools
        ]

    @staticmethod
    def _extract_tool_calls(response: Any) -> Optional[List[Dict[str, Any]]]:
        calls = [
            {
                "id": block.id,
                "type": "function",
                "function": {"name": block.name, "arguments": json.dumps(block.input)},
            }
            for block in getattr(response, "content", [])
            if getattr(block, "type", None) == "tool_use"
        ]
        return calls if calls else None

    @staticmethod
    def _extract_text(response: Any) -> Optional[str]:
        for block in getattr(response, "content", []):
            if getattr(block, "type", None) == "text":
                return block.text
        return None

    @emits(EventTypes.LLM)
    async def invoke(
        self,
        context: "LLMContext",
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> StandardLLMResponse:
        self.active_requests += 1
        try:
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            tools = kwargs.pop("tools", None)

            filtered = FilterManager.for_target("messages", "anthropic").apply(messages)
            system, body = self._split_system(filtered)
            body = self._convert_messages(body)

            params: Dict[str, Any] = {
                "model": self.model,
                "messages": body,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }
            if system:
                params["system"] = system
            if tools:
                params["tools"] = self._convert_tools(tools)

            response = await self.client.messages.create(**params)

            usage = Usage.create(
                f"anthropic/{self.model}",
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return LLMResponseFactory.create(
                content=self._extract_text(response),
                tool_calls=self._extract_tool_calls(response),
                usage=usage,
                raw_response=response,
            )
        finally:
            self.active_requests -= 1

    @emits(EventTypes.LLM)
    async def astream(
        self,
        context: "LLMContext",
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> StreamingLLMResponse:
        self.active_requests += 1
        try:
            temperature = kwargs.pop("temperature", self.temperature)
            max_tokens = kwargs.pop("max_tokens", self.max_tokens)
            tools = kwargs.pop("tools", None)
            budget = kwargs.pop("budget", None)
            completion_type = kwargs.pop("completion_type", "hard_stop")

            filtered = FilterManager.for_target("messages", "anthropic").apply(messages)
            system, body = self._split_system(filtered)
            body = self._convert_messages(body)

            params: Dict[str, Any] = {
                "model": self.model,
                "messages": body,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **kwargs,
            }
            if system:
                params["system"] = system
            if tools:
                params["tools"] = self._convert_tools(tools)

            stream = await self.client.messages.create(**params)

            return StreamingLLMResponse(
                stream=stream,
                model=self.model,
                provider="anthropic",
                metadata={"temperature": temperature, "tools": tools is not None},
                budget=budget,
                completion_type=completion_type,
            )
        finally:
            self.active_requests -= 1

