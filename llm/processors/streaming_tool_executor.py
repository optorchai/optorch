"""Streaming tool execution processor - injects tool loop callback into responses"""

from typing import List, Dict, Any, Callable, Awaitable, AsyncIterator, cast
from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.errors import error_context
from optorch.errors.exceptions import LLMError, ToolExecutionError


class StreamingToolExecutor(BaseLLMProcessor):
    """Injects tool execution callback into streaming responses
    
    Responses handle orchestration (_tool_handler wraps _process_stream),
    but tool execution logic injected here at lifecycle layer.
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.TOOL_EXECUTION
    
    def should_run(self, context: LLMContext) -> bool:
        """Only run for streaming responses with tools"""
        return context.streaming and super().should_run(context)
    
    async def process(self, context: LLMContext) -> None:
        """Inject tool executor callback into streaming response"""
        tools = context.config.get("tools")
        if not tools and context.config.get("invoke_kwargs"):
            tools = context.config["invoke_kwargs"].get("tools")
        
        if not context.streaming or not context.response:
            return
        
        if not tools:
            return
        
        streaming_response = cast(StreamingLLMResponse, context.response)
        streaming_response._tool_executor_callback = self._create_callback(context)
    
    def _create_callback(self, context: LLMContext) -> Callable[[List[Dict[str, Any]]], Awaitable[AsyncIterator]]:
        """Create async callback that executes tools and re-invokes LLM
        
        Returns:
            Async callable that takes tool_calls list and returns new stream (AsyncIterator)
        """
        
        @error_context(component="llm", phase="tool_execution")
        async def tool_handler(tool_calls: List[Dict[str, Any]]) -> AsyncIterator:
            """Execute all tool calls and return new stream"""
            from optorch.controller.node_controller import NodeController
            import json
            
            if not context.node_context or not context.node_context.controller:
                raise ToolExecutionError(
                    "No controller available in context",
                    details={"has_node_context": bool(context.node_context)}
                )
                
            tool_registry = context.node_context.controller.tools.registry()
            
            tool_results: List[Dict[str, str]] = []
            for tc in tool_calls:
                try:
                    args = tc.get("function", {}).get("arguments", {})
                    args = json.loads(args) if isinstance(args, str) else args
                    result = await tool_registry.execute(tool_name=tc["function"]["name"], context=context.node_context, **args)
                    
                    if isinstance(result, dict):
                        if result.get("success") is False:
                            result_str = f"Error: {result.get('error', 'Unknown error')}"
                            if result.get('details'):
                                result_str += f"\nDetails: {json.dumps(result['details'])}"
                        else:
                            result_str = json.dumps(result) if result.get("success") else str(result)
                    else:
                        result_str = str(result)
                    
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_str
                    })
                except Exception as e:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", "unknown"),
                        "content": f"Error: {str(e)}"
                    })
            
            updated_messages: List[Dict[str, Any]] = context.messages + [
                {"role": "assistant", "tool_calls": tool_calls}
            ] + tool_results
            

            msg_index = len(context.messages)
            for tc in updated_messages[msg_index]["tool_calls"]:
                if "function" in tc and "arguments" in tc["function"]:
                    if not isinstance(tc["function"]["arguments"], str):
                        tc["function"]["arguments"] = json.dumps(tc["function"]["arguments"])
            
            invoke_kwargs = context.config.get("invoke_kwargs", {})
            
            if not context.client:
                raise LLMError(
                    "No LLM client available in context",
                    details={"has_context": bool(context)}
                )
            
            response = await context.client.astream(context, updated_messages, **invoke_kwargs)
            stream: AsyncIterator = getattr(response, '_initial_stream', getattr(response, '_raw_response'))
            return stream
        
        return tool_handler
