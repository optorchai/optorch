"""
Context extraction utilities for decorators.

Enables decorators to access NodeContext without explicit parameters.
"""

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext


def extract_context(args: tuple, kwargs: dict) -> Optional['NodeContext']:
    """
    Extract NodeContext from function args/kwargs.
    
    Tries multiple sources:
    1. Direct kwarg: func(..., context=ctx)
    2. Positional args (check all args for NodeContext)
    3. Node method: self.context (args[0].context)
    4. IntentContext: intent_context.context
    5. LLMContext: llm_context.node_context
    
    Args:
        args: Function positional arguments
        kwargs: Function keyword arguments
    
    Returns:
        NodeContext if found, else None
    """
    
    if 'context' in kwargs:
        ctx = kwargs['context']
        if _is_node_context(ctx):
            return ctx
        
        if hasattr(ctx, 'node_context'):
            node_ctx = ctx.node_context
            if _is_node_context(node_ctx):
                return node_ctx
    
    for arg in args:
        if _is_node_context(arg):
            return arg

        if hasattr(arg, 'node_context'):
            node_ctx = arg.node_context
            if _is_node_context(node_ctx):
                return node_ctx
    
    if args and hasattr(args[0], 'context'):
        ctx = args[0].context
        if _is_node_context(ctx):
            return ctx
    
    if 'intent_context' in kwargs:
        intent_ctx = kwargs['intent_context']
        if hasattr(intent_ctx, 'context'):
            ctx = intent_ctx.context
            if _is_node_context(ctx):
                return ctx
    
    if 'llm_context' in kwargs:
        llm_ctx = kwargs['llm_context']
        if hasattr(llm_ctx, 'node_context'):
            ctx = llm_ctx.node_context
            if _is_node_context(ctx):
                return ctx
    
    return None


def _is_node_context(obj: Any) -> bool:
    """Check if object is a NodeContext (duck typing to avoid circular import)"""
    if obj is None:
        return False
    
    return obj.__class__.__name__ == 'NodeContext'
