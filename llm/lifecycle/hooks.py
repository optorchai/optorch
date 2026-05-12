"""LLM Lifecycle Hooks - Execution phases for LLM invocation"""

from enum import Enum


class LLMLifecycleHook(str, Enum):
    """Lifecycle phases - execution order always same, substates control processor participation"""
    
    PRE_INVOKE = "pre_invoke"        # History retrieval, message prep, validators, budget
    INVOKE = "invoke"                # Actual LLM call
    TOOL_EXECUTION = "tool_execution"  # Tool loop handling
    POST_INVOKE = "post_invoke"      # Transformers, history persistence
    FINALIZE = "finalize"            # Metrics, costs, cleanup
    
    @classmethod
    def ordered(cls) -> list["LLMLifecycleHook"]:
        """Phases always execute in this order - substates determine which processors run"""
        return [
            cls.PRE_INVOKE,
            cls.INVOKE,
            cls.TOOL_EXECUTION,
            cls.POST_INVOKE,
            cls.FINALIZE
        ]
