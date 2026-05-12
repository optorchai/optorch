"""Cost tracker processor - FINALIZE - emits cost events and persists to session"""

from optorch.logging import get_logger
from decimal import Decimal
from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.llm.pricing import Pricing
from optorch.events.decorators import emits
from optorch.constants import EventTypes

logger = get_logger(__name__)

class CostTracker(BaseLLMProcessor):
    """Track costs, emit events, and persist session totals"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.FINALIZE
    
    @emits(EventTypes.LLM)
    async def process(self, context: LLMContext) -> None:
        """Extract cost, emit event, and save to session"""
        if not context.response:
            return
        
        cost = None
        if "cost" in context.metadata:
            cost = context.metadata["cost"]
        elif hasattr(context.response, "usage") and context.response.usage:
            cost = context.response.usage.cost
        elif hasattr(context.response, "metadata") and context.response.metadata:
            cost = context.response.metadata.get("cost")
        
        if cost is not None:
            if not isinstance(cost, Decimal):
                cost = Decimal(str(cost))
            
            total_cost = await self._persist_to_session(context, float(cost))
            
            # get session_id from state or metadata to ensure it's included even if ContextVar is lost
            session_id = None
            if context.state:
                session_id = context.state.get("session_id")
            if not session_id:
                session_id = context.metadata.get("session_id")
            
            event_data = {
                "cost": float(cost),
                "total_cost": total_cost,
                "currency": Pricing.get_currency(),
                "budget": float(context.budget) if context.budget else None,
                "budget_consumed": float(context.budget_consumed),
                "model": context.config.get("model"),
                "provider": context.config.get("provider"),
            }
            
            # explicitly set session_id if available
            if session_id:
                event_data["session_id"] = session_id
            
            logger.info(f"Cost tracked: ${cost:.4f} (session total: ${total_cost:.4f})")
            context.events.emit(f"{EventTypes.LLM}.cost", event_data, state=context.state)
    
    async def _persist_to_session(self, context: LLMContext, exchange_cost: float) -> float:
        """Save cumulative cost total to session and return new total"""
        if not context.state:
            logger.debug("No state - skipping session cost persistence")
            return exchange_cost
            
        session_id = context.state.get("session_id")
        if not session_id:
            logger.debug("No session_id - skipping session cost persistence")
            return exchange_cost
        
        session_manager = context.metadata.get('session_manager')
        if not session_manager:
            logger.debug("No session_manager - skipping session cost persistence")
            return exchange_cost
        
        session_data = await session_manager.get_data(session_id) or {}
        previous_cost = session_data.get("total_cost", 0.0)
        if isinstance(previous_cost, str):
            previous_cost = float(previous_cost)
        
        total_cost = previous_cost + exchange_cost
        
        session_data["total_cost"] = total_cost
        session_data["currency"] = Pricing.get_currency()
        
        await session_manager.set_data(session_data, session_id)
        
        logger.debug(f"Persisted session total: ${total_cost:.6f} (exchange: ${exchange_cost:.6f})")
        
        return total_cost
