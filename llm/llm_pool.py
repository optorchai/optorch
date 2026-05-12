"""
LLM Pool for parallel/sequential processing across multiple clients.
Supports mixed providers (e.g., GPT-4o + Groq in same pool).
"""
import asyncio
from optorch.logging import get_logger
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage
from optorch.llm.pool.base_strategy import LoadBalancingStrategy
from optorch.llm.pool.round_robin_strategy import RoundRobinStrategy

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext

logger = get_logger(__name__)


class LLMPool(BaseLLMClient):
    """
    Pool of LLM clients with intelligent parallel/sequential processing.
    Auto-detects optimal strategy based on token load and pool capacity.
    """
    
    def __init__(
        self,
        clients: List[BaseLLMClient],
        strategy: Optional[LoadBalancingStrategy] = None,
        name: str = "unnamed-pool"
    ):
        if not clients:
            raise ValueError("Pool requires at least one client")
        
        super().__init__(model=f"pool:{name}", tpm_limit=sum(c.tpm_limit for c in clients))
        
        self.name = name
        self.clients = clients
        self.strategy = strategy or RoundRobinStrategy()
        self.semaphores = [asyncio.Semaphore(1) for _ in clients]
    
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        """Single request - select one client from pool"""
        client = await self.strategy.select_client(self.clients, self._estimate_tokens(messages))
        client_idx = self.clients.index(client)
        
        async with self.semaphores[client_idx]:
            client.active_requests += 1
            try:
                return await client.invoke(context, messages, **kwargs)
            finally:
                client.active_requests -= 1
    
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """streaming request - select one client from pool"""
        client = await self.strategy.select_client(self.clients, self._estimate_tokens(messages))
        client_idx = self.clients.index(client)
        
        async with self.semaphores[client_idx]:
            client.active_requests += 1
            try:
                return await client.astream(context, messages, **kwargs)
            finally:
                client.active_requests -= 1
    
    async def invoke_batch(self, context: 'LLMContext', message_batches: List[List[Dict[str, Any]]], **kwargs) -> List[LLMResponse]:
        """
        Batch requests with auto-detection:
        - Light load: Sequential (avoid overhead)
        - Heavy load within capacity: Full parallel
        - Heavy load exceeding capacity: Throttled parallel
        """
        if not message_batches:
            return []
        
        total_tokens = sum(self._estimate_tokens(msg) for msg in message_batches)
        batch_count = len(message_batches)
        
        logger.debug(f"Pool {self.name}: Processing {batch_count} batches (~{total_tokens} tokens)")
        
        if total_tokens < 10000 or batch_count < 3:
            logger.debug(f"Pool {self.name}: Using sequential processing (light load)")
            return await self._invoke_sequential(context, message_batches, **kwargs)
        
        effective_tpm = self.get_effective_tpm()
        tokens_per_minute = total_tokens
        
        if tokens_per_minute < effective_tpm * 0.8:
            logger.debug(f"Pool {self.name}: Using full parallel ({batch_count} concurrent)")
            return await self._invoke_parallel(context, message_batches, **kwargs)
        else:
            logger.debug(f"Pool {self.name}: Using throttled parallel (TPM: {effective_tpm}, load: {tokens_per_minute})")
            return await self._invoke_throttled(context, message_batches, **kwargs)
    
    async def _invoke_parallel(self, context: 'LLMContext', message_batches: List[List[Dict[str, Any]]], **kwargs) -> List[LLMResponse]:
        """Full parallel - all batches at once, distributed across clients"""
        tasks = []
        for i, messages in enumerate(message_batches):
            client = self.clients[i % len(self.clients)]
            client_idx = self.clients.index(client)
            
            async def invoke_with_semaphore(c, c_idx, msg):
                async with self.semaphores[c_idx]:
                    c.active_requests += 1
                    try:
                        return await c.invoke(context, msg, **kwargs)
                    finally:
                        c.active_requests -= 1
            
            tasks.append(invoke_with_semaphore(client, client_idx, messages))
        
        return await asyncio.gather(*tasks)
    
    async def _invoke_sequential(self, context: 'LLMContext', message_batches: List[List[Dict[str, Any]]], **kwargs) -> List[LLMResponse]:
        """Sequential - one batch at a time"""
        results = []
        for messages in message_batches:
            result = await self.invoke(context, messages, **kwargs)
            results.append(result)
        return results
    
    async def _invoke_throttled(self, context: 'LLMContext', message_batches: List[List[Dict[str, Any]]], **kwargs) -> List[LLMResponse]:
        """Throttled parallel - process in waves to respect TPM limits"""
        results = []
        wave_size = len(self.clients)  # Process N at a time (where N = pool size)
        
        for i in range(0, len(message_batches), wave_size):
            wave = message_batches[i:i+wave_size]
            logger.debug(f"Pool {self.name}: Processing wave {i//wave_size + 1} ({len(wave)} batches)")
            
            wave_results = await self._invoke_parallel(context, wave, **kwargs)
            results.extend(wave_results)
            
            if i + wave_size < len(message_batches):
                await asyncio.sleep(1)
        
        return results
    
    def get_effective_tpm(self) -> int:
        """Total TPM across all clients in pool"""
        return sum(client.tpm_limit for client in self.clients)
    
    def __repr__(self):
        client_info = ", ".join([f"{c.model}" for c in self.clients])
        return f"LLMPool(name={self.name}, clients=[{client_info}], effective_tpm={self.get_effective_tpm()})"
    
    # Provider-specific methods for abstract compliance (delegate to selected client)
    async def _build_invoke_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        """Delegate to first client for param building"""
        selected_client = await self.strategy.select_client(self.clients, request_size=len(str(messages)))
        return await selected_client._build_invoke_params(messages, temperature, tools, **kwargs)
    
    async def _build_stream_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        """Delegate to first client for param building"""
        selected_client = await self.strategy.select_client(self.clients, request_size=len(str(messages)))
        return await selected_client._build_stream_params(messages, temperature, tools, **kwargs)
    
    async def _call_api(self, params: Dict[str, Any]) -> Any:
        """Delegate to selected client"""
        selected_client = await self.strategy.select_client(self.clients, request_size=len(str(params)))
        return await selected_client._call_api(params)
    
    async def _call_stream_api(self, params: Dict[str, Any]) -> Any:
        """Delegate to selected client"""
        selected_client = await self.strategy.select_client(self.clients, request_size=len(str(params)))
        return await selected_client._call_stream_api(params)
    
    def _extract_content(self, response: Any) -> str:
        """Delegate to first client"""
        return self.clients[0]._extract_content(response)
    
    def _extract_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        """Delegate to first client"""
        return self.clients[0]._extract_tool_calls(response)
    
    def _extract_usage(self, response: Any) -> Optional[Usage]:
        """Delegate to first client"""
        return self.clients[0]._extract_usage(response)
    
    def _get_provider_name(self) -> str:
        """Return pool name as provider"""
        return f"pool-{self.name}"
