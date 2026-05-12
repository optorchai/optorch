"""streaming response with async iterator"""
from optorch.logging import get_logger
from decimal import Decimal
from typing import Awaitable, List, Dict, Any, Optional, AsyncIterator, Callable, Type
from optorch.llm.responses.llm_response import LLMResponse
from optorch.llm.responses.helpers import (check_budget_exceeded, should_yield_chunk, emit_chunk_event)
from optorch.llm.responses.helpers.provider_registry import get_extractor
from optorch.llm.responses.helpers.extractor_protocol import StreamExtractor, ToolBuffer
from optorch.llm.budget import CompletionTypeRegistry, BaseCompletionType
from optorch.llm.metrics import Usage
from optorch.transformers.base_transformer import BaseTransformer
from optorch.llm.lifecycle.context import LLMContext
from optorch.utils import generate_id

logger = get_logger(__name__)

class StreamingLLMResponse(LLMResponse):
    """response for streaming llm calls"""
    
    def __init__(
        self,
        stream: AsyncIterator,
        model: Optional[str] = None,
        provider: str = "openai",
        budget: Optional[Decimal] = None,
        completion_type: str = "hard_stop",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Usage] = None,
        raw_response: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        pre_processed: bool = False
    ):
        self._model = model or "unknown"
        self._provider = provider
        self._budget = budget
        self._completion_type = completion_type
        self._initial_stream = stream
        self._pre_processed = pre_processed
        
        self._accumulated_tools: List[Dict[str, Any]] = []
        self._accumulated_usage = usage
        self._total_tokens = 0
        self._total_cost = Decimal("0")
        self._content = None
        self._transformer_metadata: Dict[str, Any] = {}
        self._stream_consumed = False
        self._context: Optional["LLMContext"] = None
        
        self._tool_executor_callback: Optional[Callable] = None
        self._response_id = generate_id()
        self._lifecycle_resume_callback: Optional[Callable[[], Awaitable[None]]] = None
        
        if pre_processed:
            self._stream = stream
        else:
            self._stream = self._get_stream(stream)
        self._tool_calls = tool_calls
        self._usage = usage
        self._raw_response = raw_response
        self._metadata = metadata
    
    def _get_stream(self, stream: AsyncIterator, processed: bool = False) -> AsyncIterator[str]:
        """deferred stream - checks for callback at iteration time
        
        Args:
            stream: async iterator to wrap
            processed: if True, stream already yields string chunks (from transformers)
        """
        async def deferred_stream() -> AsyncIterator[str]:
            try:
                if self._tool_executor_callback:
                    async for chunk in self._tool_handler():
                        yield chunk
                else:
                    if processed:
                        async for chunk in stream:
                            yield chunk
                    else:
                        async for chunk in self._process_stream(stream):
                            yield chunk
            finally:
                if not self._stream_consumed:
                    self._stream_consumed = True
                    if self._lifecycle_resume_callback:
                        await self._lifecycle_resume_callback()
        return deferred_stream()
    
    @property
    def is_stream(self) -> bool:
        return True
    
    @property
    def response_id(self) -> str:
        assert self._response_id is not None
        return self._response_id
    
    @property
    def stream(self) -> AsyncIterator:
        """access the underlying stream"""
        return self._stream
    
    @property
    def content(self) -> Optional[str]:
        """accumulated content - only available after stream consumed"""
        return self._content
    
    @property
    def tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        """tool calls from response - available after stream consumed"""
        return self._accumulated_tools if self._accumulated_tools else None
    
    @property
    def usage(self) -> Optional[Usage]:
        """usage data - available after stream consumed"""
        return self._accumulated_usage
    
    @property
    def raw_response(self) -> Optional[Any]:
        return self._raw_response
    
    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        result = self._metadata.copy() if self._metadata else {}
        result.update(self._transformer_metadata)
        return result if result else None
    
    def set_tool_executor(self, callback: Callable) -> None:
        """inject tool executor callback for multi-turn orchestration"""
        self._tool_executor_callback = callback
    
    def set_context(self, context: "LLMContext") -> None:
        """Store context reference for stream.consumed event"""
        self._context = context
    
    def set_lifecycle_resume(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Inject lifecycle resume callback - called when stream consumed to continue deferred hooks"""
        self._lifecycle_resume_callback = callback
    
    async def _tool_handler(self) -> AsyncIterator[str]:
        """orchestrate tool execution loop - wraps _process_stream"""
        current_stream: AsyncIterator = self._initial_stream
        first_iteration = True
        
        while True:
            self._accumulated_tools = []
            
            if first_iteration:
                buffered_chunks = []
                async for chunk in self._process_stream(current_stream):
                    buffered_chunks.append(chunk)
                first_iteration = False
            else:
                async for chunk in self._process_stream(current_stream):
                    yield chunk
            
            if not self._accumulated_tools or not self._tool_executor_callback:
                if 'buffered_chunks' in locals():
                    for chunk in buffered_chunks:
                        yield chunk
                break
            
            new_stream = await self._tool_executor_callback(self._accumulated_tools)
            if not new_stream:
                break
            current_stream = new_stream
    
    async def _process_stream(self, stream: AsyncIterator) -> AsyncIterator[str]:
        """single-pass accumulation - provider-agnostic"""
        extractor: Type[StreamExtractor] = get_extractor(self._provider)
        
        try:
            tool_calls_buffer: ToolBuffer = extractor.create_tool_buffer()
            content_buffer = ""
            
            completion_type: Optional[BaseCompletionType] = None
            if self._budget:
                completion_type = CompletionTypeRegistry.get(self._completion_type)
                
            async for chunk in stream:
                content = extractor.extract_content(chunk)
                tool_calls = extractor.extract_tool_calls(chunk)
                usage_data = extractor.extract_usage(chunk, self._model)
                
                if content:
                    if not self._content:
                        self._content = ""
                    self._content += content
                    
                    chunk_tokens = len(content) // 4
                    self._total_tokens += chunk_tokens
                    
                    if self._budget and completion_type:
                        stop, self._total_cost, final = check_budget_exceeded(
                            chunk_tokens, self._model, self._total_tokens,
                            self._total_cost, self._budget, completion_type, content_buffer
                        )
                        if stop:
                            if final:
                                yield final
                            break
                        
                        should_yield, content_buffer = should_yield_chunk(content, content_buffer, completion_type)
                        if should_yield:
                            emit_chunk_event(content_buffer, self._total_cost, self._total_tokens)
                            yield content_buffer
                            content_buffer = ""
                    else:
                        emit_chunk_event(content, self._total_cost, self._total_tokens)
                        yield content
                
                if tool_calls:
                    extractor.accumulate_tools(tool_calls, tool_calls_buffer)
                
                if usage_data:
                    if self._accumulated_usage:
                        self._accumulated_usage.input_tokens += usage_data.input_tokens
                        self._accumulated_usage.output_tokens += usage_data.output_tokens
                        self._accumulated_usage.total_tokens += usage_data.total_tokens
                        self._accumulated_usage.cost += usage_data.cost
                    else:
                        self._accumulated_usage = usage_data
                    
                    # store in context so FINALIZE hook can access
                    if self._context:
                        self._context.metadata["usage"] = self._accumulated_usage
                        self._context.metadata["cost"] = float(self._accumulated_usage.cost)
            
            if tool_calls_buffer:
                self._accumulated_tools = extractor.finalize_tools(tool_calls_buffer)
        
        except Exception as e:
            logger.error(f"stream processing error: {e}")
            raise
    
    async def apply_transformers(self, transformers: List[BaseTransformer], context: 'LLMContext') -> 'StreamingLLMResponse':
        """apply transformers within stream"""
        if not transformers:
            return self
        
        source_stream = self._stream
        self._stream = self._transform_stream(transformers, source_stream, context)
        
        return self
    
    async def _transform_stream(self, transformers: List[BaseTransformer], source_stream: AsyncIterator, context: 'LLMContext') -> AsyncIterator[str]:
        """wrap stream with transformer application"""
        from optorch.llm.responses.accumulators import AccumulatorManager
        
        accumulators = [AccumulatorManager.create(t) for t in transformers]
        transformed_content = ""
        
        async for chunk in source_stream:
            chunk_handled = False
            
            for i, accumulator in enumerate(accumulators):
                buffered_result = accumulator.consume(chunk)
                
                if buffered_result:
                    try:
                        transformed = await transformers[i].transform(buffered_result, context)
                        content = transformed.get("content", buffered_result)
                        if "metadata" in transformed:
                            self._transformer_metadata.update(transformed["metadata"])
                        
                        transformed_content += content
                        yield content
                        chunk_handled = True
                        break
                    except Exception as e:
                        logger.error(f"Transformer {transformers[i].__class__.__name__} failed: {e}")
                        transformed_content += buffered_result
                        yield buffered_result
                        chunk_handled = True
                        
                elif accumulator.should_passthrough():
                    try:
                        transformed = await transformers[i].transform(chunk, context)
                        content = transformed.get("content", chunk)
                        if "metadata" in transformed:
                            self._transformer_metadata.update(transformed["metadata"])
                        
                        transformed_content += content
                        yield content
                        chunk_handled = True
                        break
                    except Exception as e:
                        logger.error(f"Transformer {transformers[i].__class__.__name__} failed: {e}")
                        transformed_content += chunk
                        yield chunk
                        chunk_handled = True
                        break
            
            if not chunk_handled:
                any_buffering = any(not acc.should_passthrough() for acc in accumulators)
                if not any_buffering:
                    transformed_content += chunk
                    yield chunk
        
        for i, accumulator in enumerate(accumulators):
            remaining = accumulator.flush()
            if remaining:
                try:
                    transformed = await transformers[i].transform(remaining, context)
                    content = transformed.get("content", remaining)
                    transformed_content += content
                    yield content
                except Exception as e:
                    logger.error(f"Transformer {transformers[i].__class__.__name__} flush failed: {e}")
                    transformed_content += remaining
                    yield remaining
        
        self._content = transformed_content
