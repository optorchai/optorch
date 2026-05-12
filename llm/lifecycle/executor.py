"""LLM Lifecycle Executor - Orchestrates processor chain through lifecycle phases"""

from optorch.logging import get_logger
import inspect
from typing import Dict, List, Optional
from collections import defaultdict

from optorch.loader.auto_loader import AutoLoader
from .hooks import LLMLifecycleHook
from .context import LLMContext
from .base_processor import BaseLLMProcessor

logger = get_logger(__name__)


class LLMLifecycleExecutor:
    """Orchestrates LLM invocation through processor chain - similar to NodeController lifecycle"""
    
    def __init__(self):
        self._processors: Dict[LLMLifecycleHook, List[BaseLLMProcessor]] = defaultdict(list)
        self._initialized = False
        self.deferral_boundary = LLMLifecycleHook.POST_INVOKE  # streaming: defer everything after this
    
    def register_processor(self, processor: BaseLLMProcessor, order: int | None = None) -> None:
        """Register processor for its hook phase with optional order (lower runs first)"""
        if order is not None:
            processor.order = order
        
        hook = processor.hook
        
        if processor in self._processors[hook]:
            logger.warning(f"Processor {processor.__class__.__name__} already registered for {hook}")
            return
        
        self._processors[hook].append(processor)
        self._processors[hook].sort(key=lambda p: p.order)
        logger.debug(f"Registered {processor.__class__.__name__} for {hook} phase (order={processor.order})")
    
    def _setup_processors(self, config: Optional[Dict] = None) -> None:
        """Config-driven processor loading using AutoLoader pattern
        
        Discovers processors from config and registers them dynamically.
        Config structure in optorch.yaml:
            llm.lifecycle.processors:
                <hook_name>:
                    - class: ProcessorClassName
                      enabled: true
                      substates: [...]
        
        Args:
            config: LLM config dict (optorch.llm section, injected from main)
        """
        self._register_defaults()
        
        if not config:
            logger.debug("No additional processors from config")
            self._initialized = True
            return
        
        processor_config = config.get("lifecycle", {}).get("processors", {})
        
        if not processor_config:
            logger.debug("No additional processors from config")
            self._initialized = True
            return
        
        for hook_name, processors in processor_config.items():
            if not processors:
                continue
            
            for proc_config in processors:
                if not proc_config.get("enabled", True):
                    logger.debug(f"Skipping disabled processor: {proc_config.get('class')}")
                    continue
                
                class_name = proc_config.get("class")
                if not class_name:
                    logger.error(f"Processor config missing 'class' field: {proc_config}")
                    continue
                
                try:
                    processor_class = AutoLoader.load_class(
                        class_name,
                        item_name=class_name.lower().replace("processor", ""),
                        base_package="optorch.llm.processors"
                    )
                    
                    processor = processor_class()
                    
                    if "substates" in proc_config:
                        processor.substates = set(proc_config["substates"])
                    if "exclude_substates" in proc_config:
                        processor.exclude_substates = set(proc_config["exclude_substates"])
                    
                    self.register_processor(processor)
                    logger.debug(f"Loaded processor {class_name} for {hook_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load processor {class_name}: {e}", exc_info=True)
        
        self._initialized = True
        logger.info(f"Loaded {sum(len(procs) for procs in self._processors.values())} processors from config")
    
    def _register_defaults(self) -> None:
        """Fallback: Register core processors if config missing"""
        from optorch.llm.processors.message_builder import MessageBuilder
        from optorch.llm.processors.llm_invoke import LLMInvokeProcessor
        from optorch.llm.processors.tool_executor import ToolExecutor
        from optorch.llm.processors.streaming_tool_executor import StreamingToolExecutor
        from optorch.llm.processors.transformer_pipeline import TransformerPipeline
        from optorch.llm.processors.cost_tracker import CostTracker
        from optorch.llm.processors.usage_logger import UsageLogger
        
        self.register_processor(MessageBuilder())
        self.register_processor(LLMInvokeProcessor())
        self.register_processor(ToolExecutor())
        self.register_processor(StreamingToolExecutor())
        self.register_processor(TransformerPipeline())
        self.register_processor(CostTracker())
        self.register_processor(UsageLogger())
        
        logger.debug("Registered default processors")
    
    async def execute(self, context: LLMContext, config: Optional[Dict] = None) -> LLMContext:
        """Execute all processors through lifecycle phases - mutates context in-place
        
        Args:
            context: LLM execution context
            config: LLM config dict (optional, for processor setup)
        """
        if not self._initialized:
            self._setup_processors(config)
        
        deferred_started = False
        
        for hook in LLMLifecycleHook.ordered():
            if context.skip_remaining:
                logger.debug(f"Skipping remaining phases after {hook}")
                break
            
            if deferred_started:
                continue
            
            await self._execute_hook(hook, context)
            
            hooks_list = LLMLifecycleHook.ordered()
            current_idx = hooks_list.index(hook)
            if hook == self.deferral_boundary and current_idx < len(hooks_list) - 1:
                if context.streaming and context.response and context.response.is_stream:
                    logger.debug(f"Completed deferral boundary {hook} - deferring remaining hooks for streaming")
                    
                    async def resume_lifecycle():
                        try:
                            await self._run_deferred_hooks(context, start_after=self.deferral_boundary)
                        except Exception as e:
                            logger.error(f"Error in deferred hooks: {e}", exc_info=True)
                    
                    from optorch.llm.responses.streaming_response import StreamingLLMResponse
                    if isinstance(context.response, StreamingLLMResponse):
                        context.response.set_lifecycle_resume(resume_lifecycle)
                    deferred_started = True
        
        return context
    
    async def _execute_hook(self, hook: LLMLifecycleHook, context: LLMContext) -> None:
        """Execute all processors and user callbacks for a specific hook
        
        Args:
            hook: The lifecycle hook to execute
            context: LLM context
        """
        processors = self._processors[hook]
        user_callbacks = context.user_callbacks.get(hook, [])
        
        if not processors and not user_callbacks:
            logger.debug(f"No processors or callbacks registered for {hook}")
            return
        
        logger.debug(f"Executing {hook} phase with {len(processors)} processors, {len(user_callbacks)} user callbacks")
        
        for processor in processors:
            if not processor.should_run(context):
                logger.debug(
                    f"Skipping {processor.__class__.__name__} "
                    f"(substates={processor.substates}, active={context.active_substates})"
                )
                continue
            
            logger.debug(f"Running {processor.__class__.__name__}")
            try:
                context._current_phase = hook
                await processor.process(context)
            except Exception as e:
                logger.error(f"Processor {processor.__class__.__name__} failed in {hook}: {e}", exc_info=True)
                raise
        
        await context.wait_for_pending_tasks(timeout=3.0)

        for callback, args, kwargs in user_callbacks:
            try:
                sig = inspect.signature(callback)
                params = list(sig.parameters.values())
                
                has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
                has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
                
                if not params:
                    await callback()
                elif has_var_positional or has_var_keyword:
                    await callback(context, *args, **kwargs)
                elif len(params) >= 1:
                    await callback(context, *args, **kwargs)
                else:
                    await callback()
                    
            except Exception as e:
                logger.error(f"User callback failed in {hook}: {e}", exc_info=True)
                raise
    
    async def _run_deferred_hooks(self, context: LLMContext, start_after: LLMLifecycleHook) -> None:
        """Run all hooks after deferral boundary - called after stream consumed
        
        Args:
            context: LLM context
            start_after: Deferral boundary - run all hooks AFTER this one (e.g., POST_INVOKE means run FINALIZE+)
        """
        hooks_list = LLMLifecycleHook.ordered()
        boundary_idx = hooks_list.index(start_after)
        deferred_hooks = hooks_list[boundary_idx + 1:]
        
        logger.debug(f"Running {len(deferred_hooks)} deferred hooks after {start_after}")
     
        for hook in deferred_hooks:
            await self._execute_hook(hook, context)
    
    def get_processors(self, hook: Optional[LLMLifecycleHook] = None) -> List[BaseLLMProcessor]:
        """Get processors for specific hook or all processors"""
        if hook:
            return list(self._processors[hook])
        
        all_processors = []
        for hook in LLMLifecycleHook.ordered():
            all_processors.extend(self._processors[hook])
        return all_processors
    
    def clear_processors(self, hook: Optional[LLMLifecycleHook] = None) -> None:
        """Clear processors for specific hook or all - useful for testing"""
        if hook:
            self._processors[hook].clear()
        else:
            self._processors.clear()
        self._initialized = False
