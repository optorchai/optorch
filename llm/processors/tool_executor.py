"""Tool executor processor - TOOL_EXECUTION phase for non-streaming"""

import json
from optorch.logging import get_logger
from typing import Optional, Any

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.errors.exceptions import LLMError, ToolExecutionError
from optorch.errors import error_context

logger = get_logger(__name__)

class ToolExecutor(BaseLLMProcessor):
    """Synchronous tool execution loop for non-streaming responses"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.TOOL_EXECUTION
    
    def should_run(self, context: LLMContext) -> bool:
        """Only run for non-streaming responses"""
        return not context.streaming and super().should_run(context)
    
    @error_context(component="llm", phase="tool_execution")
    async def process(self, context: LLMContext) -> None:
        """Execute tools synchronously until no more tool_calls"""
        if not context.response or not context.response.tool_calls:
            logger.debug("No tool calls in response")
            return
        
        tools_config = context.config.get("tools")
        
        if not tools_config:
            logger.debug("No tools configured - skipping tool execution")
            return
        
        if not context.node_context or not context.node_context.controller:
            raise ToolExecutionError(
                "No controller available in context",
                details={"has_node_context": bool(context.node_context)}
            )
        
        max_iterations = 10
        iteration = 0
        
        while context.response and context.response.tool_calls and iteration < max_iterations:
            iteration += 1
            logger.debug(f"Tool execution iteration {iteration}, {len(context.response.tool_calls)} tool calls")
            
            context.messages.append({
                "role": "assistant",
                "content": context.response.content if context.response else "",
                "tool_calls": context.response.tool_calls if context.response else []
            })
            
            results = []
            for call in context.response.tool_calls:
                if isinstance(call, dict):
                    tool_name = call.get("function", {}).get("name")
                    args_str = call.get("function", {}).get("arguments", "{}")
                    tool_id = call.get("id")
                else:
                    tool_name = call.function.name
                    args_str = call.function.arguments
                    tool_id = call.id
                
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    logger.debug(f"Executing tool {tool_name} with args: {args}")
                    
                    result = await context.node_context.controller.tools.registry().execute(
                        tool_name=tool_name,
                        context=context.node_context,
                        **args
                    )
                    
                    if isinstance(result, dict):
                        if result.get("success") is False:
                            result_str = f"Error: {result.get('error', 'Unknown error')}"
                            if result.get('details'):
                                result_str += f"\nDetails: {json.dumps(result['details'])}"
                        else:
                            result_str = json.dumps(result) if result.get("success") else str(result)
                    else:
                        result_str = str(result)
                    
                    results.append((tool_id, result_str))
                    logger.debug(f"Tool {tool_name} result: {result_str}")
                    
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
                    results.append((tool_id, f"Error: {str(e)}"))
            
            for tool_id, result in results:
                context.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result
                })
            
            logger.debug("Invoking LLM with tool results")
            original_substates = context.active_substates.copy()
            context.active_substates = {"tool_result"}
            
            if not context.client:
                raise LLMError(
                    "No LLM client available in context",
                    details={"iteration": iteration}
                )
            
            try:
                context.response = await context.client.raw_invoke(
                    context.messages,
                    tools=tools_config,
                    **context.config.get("invoke_kwargs", {})
                )
            finally:
                context.active_substates = original_substates
        
        if iteration >= max_iterations:
            logger.warning(f"Tool execution stopped after {max_iterations} iterations")
