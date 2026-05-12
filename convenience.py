"""Convenience API - LangChain-like simplicity for quick LLM calls

Auto-discovers clients, supports injection, config merging.

Usage:
    import optorch
    
    # Auto-discovery
    result = await optorch.ainvoke(model="gpt-4o-mini", message="What's 2+2?")
    
    # With injected client
    from optorch.llm.clients.openai_client import OpenAIClient
    client = OpenAIClient(api_key="...", model="gpt-4o")
    result = await optorch.ainvoke(message="Hello", client=client)
    
    # With config
    result = await optorch.ainvoke(
        message="Hello",
        model="gpt-4o-mini",
        config={"api_key": "sk-...", "temperature": 0.3}
    )
"""

from optorch.logging import get_logger
import importlib
import inspect
import pkgutil
from typing import Optional, Any, Union, Callable, AsyncIterator, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.llm.base_client import BaseLLMClient

logger = get_logger(__name__)

_CLIENT_CACHE: dict[str, type] = {}
_MODEL_PATTERNS: dict[str, list[str]] = {}


def _get_secret_provider():
    """lazy load secret provider from config manager"""
    from optorch.config.manager import ConfigManager
    config_manager = ConfigManager()
    return config_manager.secret_provider


def _discover_clients() -> dict[str, type]:
    """Auto-discover all LLM clients in optorch.llm.clients"""
    if _CLIENT_CACHE:
        return _CLIENT_CACHE
    
    try:
        import optorch.llm.clients as clients_module
        
        for _, module_name, _ in pkgutil.iter_modules(clients_module.__path__):
            if module_name.endswith("_client"):
                module = importlib.import_module(f"optorch.llm.clients.{module_name}")
                
                for attr_name in dir(module):
                    if attr_name.endswith("Client") and not attr_name.startswith("Base"):
                        cls = getattr(module, attr_name)
                        if hasattr(cls, "invoke"):
                            provider = module_name.replace("_client", "")
                            _CLIENT_CACHE[provider] = cls
                            
                            if hasattr(cls, "MODEL_PATTERNS"):
                                _MODEL_PATTERNS[provider] = cls.MODEL_PATTERNS
                            
                            logger.debug(f"Discovered client: {provider} → {attr_name}")
        
        return _CLIENT_CACHE
    
    except Exception as e:
        logger.error(f"Client discovery failed: {e}", exc_info=True)
        return {}


def _detect_provider(model: str) -> str:
    """Auto-detect provider from model name using client-defined patterns"""
    model_lower = model.lower()
    
    _discover_clients()
    
    for provider, patterns in _MODEL_PATTERNS.items():
        if any(pattern in model_lower for pattern in patterns):
            return provider
    
    available = list(_CLIENT_CACHE.keys())
    
    if not available:
        from optorch.errors.exceptions import ConfigurationError
        raise ConfigurationError("No LLM clients discovered. Check optorch.llm.clients/")
    
    from optorch.errors.exceptions import ConfigurationError
    raise ConfigurationError(
        f"Could not auto-detect provider for model '{model}'.\n"
        f"Available providers: {available}\n"
        f"Specify explicitly: ainvoke(..., provider='openai')\n"
        f"Or add MODEL_PATTERNS to client class"
    )


def _create_client(
    model: str,
    provider: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> "BaseLLMClient":
    """Create client with auto-discovery and config merging"""
    from optorch.errors.exceptions import ConfigurationError
    
    if not provider:
        provider = _detect_provider(model)
    
    clients = _discover_clients()
    client_class = clients.get(provider)
    
    if not client_class:
        raise ConfigurationError(
            f"No client found for provider '{provider}'. "
            f"Available: {list(clients.keys())}"
        )
    
    client_config = config.copy() if config else {}
    
    if hasattr(client_class, "get_default_config"):
        defaults = client_class.get_default_config(model)
        for key, value in defaults.items():
            client_config.setdefault(key, value)
    else:
        client_config.setdefault("model", model)
        
        secret_provider = _get_secret_provider()
        env_key = f"{provider.upper()}_API_KEY"
        api_key = secret_provider.get(env_key)
        if api_key:
            client_config.setdefault("api_key", api_key)
        
        if provider == "ollama":
            base_url = secret_provider.get("OLLAMA_HOST", "http://localhost:11434")
            client_config.setdefault("base_url", base_url)
        else:
            client_config.setdefault("max_tokens", 4096)
    
    sig = inspect.signature(client_class.__init__)
    accepted_params = set(sig.parameters.keys()) - {'self'}
    filtered_config = {k: v for k, v in client_config.items() if k in accepted_params}
    
    if provider != "ollama" and not filtered_config.get("api_key"):
        env_key = f"{provider.upper()}_API_KEY"
        raise ConfigurationError(
            f"{env_key} required for {provider}.\n"
            f"Set via environment or config: ainvoke(..., config={{'api_key': '...'}})"
        )
    
    return client_class(**filtered_config)


async def ainvoke(
    message: Union[str, list[dict[str, str]]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    client: Optional["BaseLLMClient"] = None,
    config: Optional[dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    tools: Optional[list[Callable]] = None,
    **kwargs: Any
) -> dict[str, Any]:
    """Async LLM call with auto-discovery, injection, and config merging.
    
    Args:
        message: User message (str) or messages array (list)
        model: Model name (auto-detects provider if not specified)
        provider: Explicit provider (openai, groq, ollama, anthropic)
        client: Pre-configured client instance (bypasses auto-discovery)
        config: Config dict to merge with defaults (api_key, base_url, etc.)
        temperature: LLM temperature (default: 0.7)
        max_tokens: Max tokens for response
        tools: List of callable functions (auto-converted to tool schemas)
        **kwargs: Additional invoke parameters
        
    Returns:
        dict with:
            - content: str - Response text
            - model: str - Model used
            - provider: str - Provider used (if detected)
            - usage: dict - Token usage info
            - raw: Response object
            
    Examples:
        # Auto-discovery from model name
        result = await ainvoke("What's 2+2?", model="gpt-4o-mini")
        
        # Explicit provider
        result = await ainvoke("Hello", model="llama3.2", provider="ollama")
        
        # Injected client
        from optorch.llm.clients.openai_client import OpenAIClient
        client = OpenAIClient(api_key="...", model="gpt-4o")
        result = await ainvoke("Hello", client=client)
        
        # With config override
        result = await ainvoke(
            message="Hello",
            model="gpt-4o-mini",
            config={"api_key": "sk-custom", "temperature": 0.3}
        )
        
        # With tools
        def calculator(expr: str) -> str:
            return str(eval(expr))
        
        result = await ainvoke(
            message="What's 15 * 23?",
            model="gpt-4o-mini",
            tools=[calculator]
        )
    """
    from optorch.errors.exceptions import ConfigurationError
    
    if isinstance(message, str):
        messages = [{"role": "user", "content": message}]
    else:
        messages = message
    
    if client is None:
        if not model:
            raise ConfigurationError("Either 'model' or 'client' must be provided")
        client = _create_client(model, provider, config)
        detected_provider = provider or _detect_provider(model)
    else:
        detected_provider = client.__class__.__name__.replace("Client", "").lower()
        model = model or getattr(client, "model", "unknown")
    
    invoke_kwargs = kwargs.copy()
    if tools:
        tool_schemas = []
        for tool_func in tools:
            if hasattr(tool_func, "__tool_schema__"):
                tool_schemas.append({
                    "type": "function",
                    "function": tool_func.__tool_schema__
                })
            else:
                import inspect
                sig = inspect.signature(tool_func)
                params: dict[str, Any] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                
                for param_name, param in sig.parameters.items():
                    params["properties"][param_name] = {"type": "string"}
                    if param.default == inspect.Parameter.empty:
                        params["required"].append(param_name)
                
                tool_schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool_func.__name__,
                        "description": tool_func.__doc__ or f"Call {tool_func.__name__}",
                        "parameters": params
                    }
                })
        
        invoke_kwargs["tools"] = tool_schemas
    
    response = await client.raw_invoke(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **invoke_kwargs
    )
    
    return {
        "content": response.content or "",
        "model": model,
        "provider": detected_provider,
        "usage": response.usage.to_dict() if hasattr(response, "usage") and response.usage else None,
        "raw": response
    }


def invoke(
    message: Union[str, list[dict[str, str]]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    client: Optional["BaseLLMClient"] = None,
    config: Optional[dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    tools: Optional[list[Callable]] = None,
    **kwargs: Any
) -> dict[str, Any]:
    """Sync wrapper for ainvoke - runs in new event loop.
    
    Use this if you're not already in an async context.
    
    Example:
        result = invoke("What's 2+2?", model="gpt-4o-mini")
        print(result["content"])
    """
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
        raise RuntimeError(
            "invoke() cannot be called from async context. "
            "Use ainvoke() instead."
        )
    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            return asyncio.run(ainvoke(
                message=message,
                model=model,
                provider=provider,
                client=client,
                config=config,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                **kwargs
            ))
        else:
            raise


async def astream(
    message: Union[str, list[dict[str, str]]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    client: Optional["BaseLLMClient"] = None,
    config: Optional[dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs: Any
) -> AsyncIterator[str]:
    """Stream LLM response with auto-provider detection.
    
    Args:
        message: User message (str) or messages array (list)
        model: Model name (auto-detects provider if not specified)
        provider: Explicit provider
        client: Pre-configured client instance
        config: Config dict to merge with defaults
        temperature: LLM temperature
        max_tokens: Max tokens for response
        **kwargs: Additional parameters
        
    Yields:
        str: Chunks of response text
        
    Example:
        async for chunk in astream("Tell me a story", model="gpt-4o-mini"):
            print(chunk, end="", flush=True)
    """
    from optorch.errors.exceptions import ConfigurationError
    
    if isinstance(message, str):
        messages = [{"role": "user", "content": message}]
    else:
        messages = message
    
    if client is None:
        if not model:
            raise ConfigurationError("Either 'model' or 'client' must be provided")
        client = _create_client(model, provider, config)
    
    response = await client.raw_astream(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )
    
    async for chunk in response.stream:
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content


__all__ = [
    "invoke",
    "ainvoke",
    "astream",
]
