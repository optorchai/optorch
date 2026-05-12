"""run tools in parallel when possible"""

import asyncio
from optorch.logging import get_logger
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.errors import error_context
from optorch.events import EventTypes

logger = get_logger(__name__)


@dataclass
class ToolResult:
    # tools dont care about your feelings
    tool_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class ParallelToolExecutor(BaseLLMProcessor):
    # because waiting sucks
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.TOOL_EXECUTION
    
    @error_context(component="llm", phase="tool_execution")
    async def process(self, context: LLMContext) -> None:
        response = context.response
        if not response or not hasattr(response, 'tool_calls') or not response.tool_calls:
            logger.debug("No tool calls - skipping parallel execution")
            return
        
        tool_calls = response.tool_calls
        if not tool_calls:
            return
        
        batches = self._detect_dependencies(tool_calls)
        
        all_results = []
        for batch_num, batch in enumerate(batches, 1):
            logger.debug(f"Executing tool batch {batch_num}/{len(batches)}: {[t['function']['name'] for t in batch]}")
            
            batch_results = await self._execute_batch(context, batch, all_results)
            all_results.extend(batch_results)
        
        context.metadata["parallel_tool_results"] = [r.result for r in all_results if r.success]
        
        successful = [r for r in all_results if r.success]
        failed = [r for r in all_results if not r.success]
        
        context.events.emit(EventTypes.LLM, {
            "event": "parallel_tools_complete",
            "total_tools": len(tool_calls),
            "successful": len(successful),
            "failed": len(failed),
            "batches": len(batches),
            "avg_duration_ms": sum(r.duration_ms for r in successful if r.duration_ms) / len(successful) if successful else 0
        })
    
    def _detect_dependencies(self, tool_calls: List[Dict]) -> List[List[Dict]]:
        batches = []
        current_batch = []
        
        executed_tools = set()
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('function', {}).get('name', '')
            tool_args = tool_call.get('function', {}).get('arguments', {})
            
            has_dependency = self._references_previous_results(tool_args, executed_tools)
            
            if has_dependency and current_batch:
                batches.append(current_batch)
                current_batch = [tool_call]
            else:
                current_batch.append(tool_call)
            
            executed_tools.add(tool_name)
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _references_previous_results(self, args: Dict, executed_tools: set) -> bool:
        if not args or not executed_tools:
            return False
        
        args_str = str(args).lower()
        
        for tool_name in executed_tools:
            if tool_name.lower() in args_str:
                return True
            
        dependency_keywords = ['result', 'output', 'response', 'data_from']
        return any(keyword in args_str for keyword in dependency_keywords)
    
    async def _execute_batch(self, context: LLMContext, batch: List[Dict], previous_results: List[ToolResult]) -> List[ToolResult]:
        if len(batch) == 1:
            return [await self._execute_single_tool(context, batch[0])]
        
        logger.debug(f"Parallel execution of {len(batch)} tools")
        
        tasks = [self._execute_single_tool(context, tool_call) for tool_call in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_id = batch[i].get('id', f'tool_{i}')
                final_results.append(ToolResult(
                    tool_id=tool_id,
                    success=False,
                    result=None,
                    error=str(result)
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _execute_single_tool(self, context: LLMContext, tool_call: Dict) -> ToolResult:
        import time
        
        tool_id = tool_call.get('id', 'unknown')
        tool_name = tool_call.get('function', {}).get('name', 'unknown')
        
        start_time = time.time()
        
        try:
            if not context.node_context or not context.node_context.controller:
                raise ValueError("No controller available in context")
            
            tool = context.node_context.controller.tools.registry().get(tool_name)
            if not tool:
                raise ValueError(f"Tool '{tool_name}' not found in registry")
            
            args = tool_call.get('function', {}).get('arguments', {})
            result = await tool.execute(**args)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.debug(f"Tool {tool_name} completed in {duration_ms}ms")
            
            return ToolResult(
                tool_id=tool_id,
                success=True,
                result=result,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.error(f"Tool {tool_name} failed after {duration_ms}ms: {e}")
            
            return ToolResult(
                tool_id=tool_id,
                success=False,
                result=None,
                error=str(e),
                duration_ms=duration_ms
            )