# Optorch

Lightweight, modular, event-driven AI orchestration framework. Built for production workflows with instance-based dependency injection, pluggable backends, and a clean node-based execution model.

## Why Optorch?

A framework that gets out of your way and lets you build exactly the workflow you need.

**No global state.** Everything lives in an `ApplicationContainer` instance. You can run multiple orchestrators side-by-side with different configs — useful for multi-tenant systems or A/B testing different LLM pipelines.

**No magic.** Nodes are plain Python classes. Tools are plain functions. There are no decorators that secretly mutate behaviour, no hidden chains. If something breaks, the stack trace points at your code.

**Config-driven, not code-driven.** Switch from GPT-4o to Llama 3 without touching a single line of Python — change the config. Add a transformer, swap a session backend, change routing logic — all in YAML.

**Production-ready from day one.** Built-in structured logging, Prometheus metrics, budget enforcement, event emission, session persistence, retry/escalation, and a full test utilities module.

**Streaming first.** SSE streaming is a first-class citizen. `StandardNode` detects streaming context automatically and switches to `astream()` with no code changes.

**Extensible without forking.** The extension system lets you add servers, analytics, Kafka workers, interactive forms, and notifications as separate installable packages that plug in cleanly without touching the core.

---

## Table of Contents

- [Installation](#installation)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Orchestrator](#orchestrator)
  - [Nodes](#nodes)
  - [State](#state)
  - [LLM Clients & Pools](#llm-clients--pools)
  - [LLM Lifecycle & Processors](#llm-lifecycle--processors)
  - [Prompt Manager & Fragments](#prompt-manager--fragments)
  - [Routing](#routing)
  - [Tools](#tools)
  - [Transformers](#transformers)
  - [Intents](#intents)
  - [Session Management](#session-management)
  - [Events](#events)
  - [History](#history)
- [Configuration](#configuration)
  - [Config Providers](#config-providers)
  - [Hot-Reload](#hot-reload)
  - [Secrets Providers](#secrets-providers)
  - [optorch.yaml](#optorchyaml)
  - [nodes.yaml](#nodesyaml)
- [Storage](#storage)
- [Caching](#caching)
- [Identity](#identity)
- [Filters](#filters)
- [Error Handling](#error-handling)
- [Prometheus Metrics](#prometheus-metrics)
- [Retry & Escalation](#retry--escalation)
- [Transport](#transport)
- [MCP Integration](#mcp-integration)
- [Embeddings & Vector Stores](#embeddings--vector-stores)
- [Module Reference](#module-reference)
- [Convenience API](#convenience-api)
- [Testing](#testing)
- [Extensions](#extensions)
- [Licence](#licence)

---

## Installation

```bash
pip install optorch
```

Optional extras:

```bash
pip install optorch[mcp]         # MCP tool server integration
pip install optorch[embeddings]  # vector stores + embedding providers
pip install optorch[all]         # everything
```

From source:

```bash
git clone git@github.com:crismc/optorch.git
cd optorch
pip install -e .
```

---

## Prerequisites

Before running anything, you need API keys for whichever LLM providers you intend to use. Optorch reads these from environment variables — never put keys directly in config files.

Create a `.env` file at the root of your project (optorch loads it automatically via `python-dotenv`):

```bash
# LLM providers
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
ANTHROPIC_API_KEY=sk-ant-...

# Storage (required for timescale/mysql backends)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Redis (required for redis session/cache backends)
REDIS_URL=redis://localhost:6379

# Identity JWT signing secret (required if using identity subsystem)
JWT_SECRET=your-secret-here

# Config/secrets provider override (optional)
OPTORCH_CONFIG_PROVIDER=yaml      # yaml | database
OPTORCH_SECRET_PROVIDER=env       # env | aws | vault
OPTORCH_CONFIG_DIR=config         # default: "config"
OPTORCH_ENV=production            # controls PII filter behaviour
```

Add `.env` to `.gitignore` — never commit it.

---

## Quick Start

### One-liner LLM call

```python
import asyncio
import optorch

async def main():
    result = await optorch.ainvoke(model="gpt-4o-mini", message="What's the capital of France?")
    print(result.content)

asyncio.run(main())
```

### Streaming

```python
async for chunk in optorch.astream(model="gpt-4o", message="Tell me a story"):
    print(chunk.content, end="", flush=True)
```

### Full workflow with nodes

```python
import asyncio
from optorch import Orchestrator
from optorch.nodes import BaseNode
from optorch.state import BaseState

class GreetingNode(BaseNode):
    async def execute(self, state: BaseState) -> BaseState:
        name = state.get("name", "world")
        state.set("response", f"Hello, {name}!")
        return state

    def route(self, state: BaseState) -> str | None:
        return None  # end workflow

def app_hooks(container):
    container.node_controller.nodes.register("greeting", GreetingNode)

async def main():
    orchestrator = await Orchestrator.create_async(app_hooks=app_hooks)
    result = await orchestrator.execute("greeting", "say hello", session_id="abc123")
    print(result.get("response"))

asyncio.run(main())
```

---

## Core Concepts

### Orchestrator

The entry point. Creates and manages the `ApplicationContainer` — wiring config, LLM clients, session, events, and all registries. There is no singleton; each `Orchestrator` instance has its own container, so you can run multiple side by side with different configurations.

```python
from optorch import Orchestrator

# Sync (blocking) — do not call from inside async context or FastAPI
orchestrator = Orchestrator.create(
    config_path="config",        # directory to load YAML from (default: "config")
    entry_node="my_node",        # override the default entry point node
    app_hooks=my_hooks_fn,       # function to register nodes/tools/intents
    config_manager=...,          # inject a pre-built ConfigManager (optional)
    llm="gpt-4o",                # runtime config override — maps to optorch.llm.model
    temperature=0.5,             # any config key can be overridden as a kwarg
    prompts={"my_node": "..."},  # inline prompt dict or callable(name)->str
    prompts_dir="prompts/",      # override prompts directory
)

# Async — use this inside FastAPI, Jupyter, or any existing event loop
orchestrator = await Orchestrator.create_async(app_hooks=my_hooks_fn)

# Execute a workflow turn
result = await orchestrator.execute(
    node="my_node",          # node to start at
    message="user input",    # added to state as the user message
    session_id="sess-123",   # optional — generated if omitted; same ID = same session
)
```

The `app_hooks` function receives the fully-initialised `ApplicationContainer` and is where you wire everything together:

```python
def app_hooks(container):
    from myapp.nodes import MyNode, ReviewNode
    from myapp.tools import search_tool, store_tool
    from myapp.transformers import ExtractJsonTransformer
    from myapp.intents import ValidateOutputIntent

    # Nodes
    container.node_controller.nodes.register("my_node", MyNode)
    container.node_controller.nodes.register("review_node", ReviewNode)

    # Tools
    container.node_controller.tools.register("search", search_tool)
    container.node_controller.tools.register("store", store_tool)

    # Transformers
    container.node_controller.transformers.register("extract_json", ExtractJsonTransformer)

    # Intents
    container.node_controller.intents.register("validate_output", ValidateOutputIntent())
```

---

### Nodes

Nodes are the unit of work. Each node has an `execute()` method (required) and a `route()` method (optional — returns the next node name or `None` to end).

Three base classes are provided:

#### BaseNode

Manual control — no automatic LLM wiring. Implement `execute()` yourself:

```python
from optorch.nodes import BaseNode
from optorch.state import BaseState

class MyNode(BaseNode):
    async def execute(self, state: BaseState) -> BaseState:
        data = state.get("input")
        state.set("output", process(data))
        return state

    def route(self, state: BaseState) -> str | None:
        return "next_node" if state.get("continue") else None
```

#### StandardNode

Automatically invokes the configured LLM. Override `route()` and optionally set fragments before the call:

```python
from optorch.nodes import StandardNode
from optorch.state import BaseState

class AnalysisNode(StandardNode):
    async def execute(self, state: BaseState) -> BaseState:
        # inject dynamic content into system prompt before LLM call
        self.set_fragment("customer_tier", state.get("tier", "standard"))
        return await super().execute(state)  # triggers LLM invocation

    def route(self, state: BaseState) -> str | None:
        if state.get("needs_escalation"):
            return "escalation_node"
        return None
```

#### CoordinatorNode

For multi-phase workflows. Manages phase tracking, child node routing, and workflow state transitions. Subclass and implement `execute()`:

```python
from optorch.nodes import CoordinatorNode
from optorch.state import BaseState

class WorkflowCoordinator(CoordinatorNode):
    async def execute(self, state: BaseState) -> BaseState:
        phase = state.get("phase", "research")
        if phase == "research":
            state = await self.call("research_node", state)
        elif phase == "draft":
            state = await self.call("draft_node", state)
        return state
```

#### RetryCoordinator

Extends `CoordinatorNode` with built-in escalation support — for when a retry handler exhausts all attempts and needs to return a graceful user message:

```python
from optorch.retry import RetryCoordinator

class MyCoordinator(RetryCoordinator):
    async def execute(self, state: BaseState) -> BaseState:
        if state.get("market_research_error"):
            return self.escalate(
                state=state,
                phase="market_research",          # stored in PENDING_PHASE for resumption
                template="market_research_failed",  # prompt template name
                error_key="market_research_error",  # state key with the error message
                context_key="market_data",          # optional extra context key
            )
        return state
```

`escalate()` sets `NEEDS_USER_INPUT` in state and formats a tone-aware user message via the prompt template. The `PENDING_PHASE` and `PENDING_PHASE_CONTEXT` keys allow the coordinator to resume from where it failed on the next turn.

#### Node properties (available inside `execute()`)

| Property              | Type             | Description                                     |
| --------------------- | ---------------- | ----------------------------------------------- |
| `self.name`           | `str`            | Node name as registered                         |
| `self.config`         | `dict`           | Node config dict from `nodes.yaml`              |
| `self.state`          | `BaseState`      | Current execution state                         |
| `self.controller`     | `NodeController` | Access to all registries and subsystems         |
| `self.event_emitter`  | `EventEmitter`   | Emit custom events                              |
| `self.prompt_manager` | `PromptManager`  | Load prompt templates and set fragment values   |
| `self.tools`          | `list`           | Tool schemas for LLM tool-calling (from config) |

#### Node methods

```python
# Call another node and come back here when it's done
result_state = await self.call("validation_node", state)

# Jump to another node — does not return
await self.goto("error_node", state)

# Execute a registered tool directly
result = await self.tool("my_tool", param1="value", param2=42)

# Inject a dynamic value into the system prompt before LLM invocation
self.set_fragment("fragment_name", "value")

# Register a callback to fire at a specific LLM lifecycle hook
self.llm_callback(state, LLMLifecycleHook.POST_INVOKE, my_async_callback)
```

---

### State

State is the data bag flowing through the workflow. It's dict-like with helpers for messages and entities. All methods are chainable.

```python
from optorch.state import State

state = State()

# Basic access
state.set("key", "value")
value = state.get("key", default="fallback")
state.update({"key1": "a", "key2": "b"})
exists = state.has("key")
state.remove("key")
data = state.to_dict()

# Merge two states (other takes precedence)
merged = state.merge(other_state)

# Chat messages
state.add_message("user", "Hello", metadata={"source": "api"})
state.add_message("assistant", "Hi there")
messages = state.get_messages()          # List[Message]
dicts = state.get_messages_as_dicts()    # List[dict] — for JSON serialisation

# Typed entities (structured extracted data)
state.set_entity("tariff", {"name": "Standard", "rate": 0.25})
tariff = state.get_entity("tariff")
has_tariff = state.has_entity("tariff")
```

`StreamingState` wraps an async generator for SSE streaming. It is returned automatically by `StandardNode` when `streaming: true` is set in node config. Callers iterate over it chunk by chunk — they do not need to know whether the response is buffered or streaming.

`StateFactory` creates the correct state subtype based on the request context:

```python
from optorch.state import StateFactory
state = StateFactory.create(streaming=True)
```

---

### LLM Clients & Pools

LLM clients are defined in config and pooled in the `LLMRegistry`. Each named entry in `llms:` becomes a client available to any node.

#### Supported providers

| Provider  | `provider` value | Notes                                |
| --------- | ---------------- | ------------------------------------ |
| OpenAI    | `openai`         | GPT-4o, GPT-4-turbo, o1, etc.        |
| Groq      | `groq`           | Llama 3, Mixtral, Gemma — ultra-fast |
| Ollama    | `ollama`         | Local models — no API key required   |
| Anthropic | `anthropic`      | Claude 3.5/3/4 — `pip install anthropic` required |

#### Configuration

```yaml
llms:
  default:
    provider: openai
    model: gpt-4o
    key_prefix: OPENAI_API_KEY # name of env var holding the key
    temperature: 0.7
    max_tokens: 2048
    timeout: 30
    streaming: false

  fast:
    provider: groq
    model: llama-3.3-70b-versatile
    key_prefix: GROQ_API_KEY
    temperature: 0.3
    timeout: 15

  local:
    provider: ollama
    model: llama3
    base_url: http://localhost:11434 # no key needed
    temperature: 0.5

  # Additional model parameters
  creative:
    provider: openai
    model: gpt-4o
    key_prefix: OPENAI_API_KEY
    temperature: 1.2
    top_p: 0.9
    frequency_penalty: 0.5
    presence_penalty: 0.3
    stop: ["###", "END"]
    completion_type: sentence # streaming budget: hard_stop | sentence | paragraph | min_tokens

  # Anthropic — system messages extracted automatically, tools converted from OpenAI schema format
  claude:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    key_prefix: ANTHROPIC_API_KEY
    temperature: 0.5
    max_tokens: 4096          # required by Anthropic API — defaults to 4096 if omitted
    streaming: false
```

#### LLM Pools

Pools distribute calls across multiple clients with load balancing and automatic fallback:

```yaml
llm_pools:
  resilient:
    clients: [default, fast] # named LLM entries to include
    strategy: round_robin # round_robin | least_busy | weighted
    fallback: true # try next client on failure
```

Reference a pool in a node the same way as a single client:

```yaml
nodes:
  my_node:
    llm: resilient # pool name works exactly like client name
```

#### Provider fallback processor

The `ProviderFallback` processor (opt-in via config) automatically retries failed LLM calls across all registered providers before raising an error. Enable it under `llm.lifecycle.processors`:

```yaml
llm:
  lifecycle:
    processors:
      invoke:
        - class: ProviderFallback
          enabled: true
```

---

### LLM Lifecycle & Processors

Every LLM call passes through a five-phase pipeline. Processors are registered to specific phases and run in order. You can add your own processors without touching core code.

#### Phases (in execution order)

| Phase            | What happens                                                        |
| ---------------- | ------------------------------------------------------------------- |
| `PRE_INVOKE`     | Build messages, load history, check response cache, validate budget |
| `INVOKE`         | Execute the actual LLM API call                                     |
| `TOOL_EXECUTION` | Run tool calls returned by the LLM (loops until no more tool calls) |
| `POST_INVOKE`    | Apply transformers, persist history, cache the response             |
| `FINALIZE`       | Track cost, emit metrics, run suggestions generator, cleanup        |

For streaming responses the pipeline defers everything after `POST_INVOKE` until the stream is consumed — processors before `POST_INVOKE` run immediately, the rest run after the caller has finished iterating.

#### Built-in processors

| Processor                  | Phase            | What it does                                                                           |
| -------------------------- | ---------------- | -------------------------------------------------------------------------------------- |
| `MessageBuilder`           | `PRE_INVOKE`     | Loads system prompt, injects fragments, extracts user message from state               |
| `ResponseCache`            | `PRE_INVOKE`     | Checks cache keyed on message hash — skips LLM call on hit                             |
| `LLMInvokeProcessor`       | `INVOKE`         | Calls the LLM client. Emits `llm.start` / `llm.complete` events                        |
| `ProviderFallback`         | `INVOKE`         | On failure, retries across all registered providers before raising                     |
| `ToolExecutor`             | `TOOL_EXECUTION` | Synchronous tool loop — executes tool calls and re-invokes LLM until no more tools     |
| `ParallelToolExecutor`     | `TOOL_EXECUTION` | Runs independent tool calls concurrently where the LLM requests multiple at once       |
| `StreamingToolExecutor`    | `TOOL_EXECUTION` | Streaming-aware tool loop — handles tool calls within streaming responses              |
| `ToolResultCache`          | `TOOL_EXECUTION` | Caches tool call results — identical arguments return cached result without re-calling |
| `TransformerPipeline`      | `POST_INVOKE`    | Applies configured transformers to response content                                    |
| `ResponseCachePersistence` | `POST_INVOKE`    | Writes the LLM response to cache for `ResponseCache` to hit on future calls            |
| `CostTracker`              | `FINALIZE`       | Calculates cost from token usage, emits `llm.cost` event, persists session totals      |
| `UsageLogger`              | `FINALIZE`       | Logs token usage per call                                                              |
| `SuggestionsGenerator`     | `FINALIZE`       | Generates contextual follow-up suggestions as a non-blocking background task           |
| `EvaluationCapture`        | `FINALIZE`       | Captures LLM call data for evaluation pipelines (analytics extension)                  |
| `PromptRegistration`       | `PRE_INVOKE`     | Registers prompt provider from node config before message building                     |

#### Adding a custom processor

Subclass `BaseLLMProcessor`, set the `hook` property, and register:

```python
from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext

class MyAuditProcessor(BaseLLMProcessor):

    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.FINALIZE

    async def process(self, context: LLMContext) -> None:
        await audit_log(
            model=context.config.get("model"),
            tokens=context.response.usage.total_tokens if context.response else 0,
            session_id=context.state.get("session_id") if context.state else None,
        )
```

Register via config (auto-loaded by `AutoLoader`):

```yaml
llm:
  lifecycle:
    processors:
      finalize:
        - class: MyAuditProcessor
          enabled: true
          substates: [default] # only run for normal (non-tool-result) invocations
```

Or register directly via the executor at runtime:

```python
container.llm_manager._executor.register_processor(MyAuditProcessor(), order=99)
```

The `substates` field controls which invocation context runs the processor: `default` for normal LLM calls, `tool_result` for the re-invocations that happen after tool execution.

#### Budget cascade

`LLMManager` resolves the active budget limit in this order: `invoke` argument → `node_budget` config key → `phase_budget` config key → `global_budget` config key. The first non-`None` value wins. This gives you fine-grained control at every scope without changing calling code.

---

### Prompt Manager & Fragments

`PromptManager` handles loading prompt templates and injecting dynamic values (fragments) before an LLM call. It is available via `self.prompt_manager` inside any node.

#### Fragments

Fragments are named placeholders injected into prompt templates before they are sent to the LLM. Two types exist:

**Static fragment** — a fixed value set at registration or at call time:

```python
from optorch.llm.fragments import Fragment

# Register a static fragment in app_hooks
prompt_manager.fragment.register(Fragment(name="product_name", content="Acme Widget"))
```

**Dynamic fragment** — a subclass that computes its value at load time:

```python
from optorch.llm.fragments import Fragment

class ToneFragment(Fragment):
    name = "tone"

    def get_value(self) -> str:
        return "formal" if is_business_hours() else "casual"
```

Set a fragment value mid-execution (before the LLM call):

```python
async def execute(self, state: BaseState) -> BaseState:
    self.set_fragment("customer_tier", state.get("tier", "standard"))
    self.set_fragment("date", datetime.now().strftime("%Y-%m-%d"))
    return await super().execute(state)
```

In the prompt template, reference fragments with `{fragment_name}`:

```markdown
You are a specialist assistant.
Tone: {tone}
Customer tier: {customer_tier}
Today's date: {date}
```

#### Prompt providers

Providers are the backends that load template strings. Multiple providers can be registered with priority ordering (lower number = tried first). The first provider that returns a non-None template wins:

```python
from optorch.llm.prompts import PromptProvider

class DatabasePromptProvider(PromptProvider):
    name = "database"

    async def load(self, prompt_name: str, fragments: dict) -> str | None:
        row = await db.fetchrow("SELECT template FROM prompts WHERE name=$1", prompt_name)
        if row:
            template = row["template"]
            for key, value in fragments.items():
                template = template.replace(f"{{{key}}}", value)
            return template
        return None

# Register with priority 1 (tried before default file provider at 99)
container.node_controller._prompt_manager.provider.register(DatabasePromptProvider(), priority=1)
```

---

### Routing

Nodes declare routing in `nodes.yaml`. Four types plus programmatic override.

**Static** — always go to the same node:

```yaml
routing:
  type: static
  next: review_node
```

**End** — terminate the workflow:

```yaml
routing:
  type: end
```

**Conditional** — branch based on a state field value:

```yaml
routing:
  type: conditional
  on: decision # state key to inspect
  conditions:
    approved: approval_node
    rejected: rejection_node
  default: review_node # fallback if value not in conditions
```

**Dynamic** — evaluate Python expressions against state. Both `state` (object) and `result` (dict) are available in scope:

```yaml
routing:
  type: dynamic
  conditions:
    - if: "state.get('confidence', 0) > 0.9"
      then: fast_path_node
    - if: "result.get('needs_human') and result.get('priority') == 'high'"
      then: human_review_node
  default: standard_node
```

Programmatic override — return from `route()` takes priority over YAML config:

```python
def route(self, state: BaseState) -> str | None:
    if state.get("error"):
        return "error_handler"
    # returning None falls through to YAML routing config
    return None
```

`return_to` — when a node uses `self.call("another_node", state)`, a `return_to` key is automatically set. The `RouteResolver` checks this first before applying any routing config, so control always returns to the caller.

---

### Tools

Tools are callable functions — async or sync — registered with the `ToolRegistry`. Their type annotations are used to auto-generate JSON schemas for LLM tool-calling (no manual schema writing required).

```python
async def search_products(query: str, max_results: int = 10, region: str = "UK") -> list[dict]:
    """Search the product catalogue"""
    return await catalogue.search(query, limit=max_results, region=region)

# Register in app_hooks
container.node_controller.tools.register("search_products", search_products)
```

Reference in node config — optorch injects the schemas into the LLM call automatically:

```yaml
nodes:
  discovery_node:
    tools:
      - search_products
      - get_pricing
```

Execute a tool directly from node code (bypasses LLM tool-calling):

```python
results = await self.tool("search_products", query="widget", max_results=5)
```

#### MCP tool lazy loading

If a tool name is not found in the local registry, the `ToolRegistry` automatically falls back to MCP servers. It discovers the correct MCP client from `MCPRegistry`, connects on demand, and registers the tool locally for subsequent calls:

```python
# This transparently calls the MCP server if "my_mcp_tool" isn't locally registered
result = await self.tool("my_mcp_tool", param="value")
```

See [MCP Integration](#mcp-integration) for MCP configuration.

#### Tool result caching

Enable `ToolResultCache` processor to cache tool call results. Identical `(tool_name, arguments)` pairs return a cached result without re-calling:

```yaml
llm:
  lifecycle:
    processors:
      tool_execution:
        - class: ToolResultCache
          enabled: true
```

---

### Transformers

Transformers post-process LLM response strings. They run as a pipeline in `POST_INVOKE` after the LLM responds, before the response is stored in state.

```python
from optorch.transformers import BaseTransformer
from optorch.llm.lifecycle.context import LLMContext
from typing import Dict, Any

class ExtractJsonTransformer(BaseTransformer):
    async def transform(self, content: str, context: LLMContext) -> Dict[str, Any]:
        import json, re
        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            return {"content": match.group(0), "metadata": {"extracted": True}}
        return {"content": content}
```

Register and reference:

```python
container.node_controller.transformers.register("extract_json", ExtractJsonTransformer)
```

```yaml
nodes:
  my_node:
    transformers:
      - extract_json
      - validate_schema
```

Transformers are applied sequentially — the output of the first becomes the input to the second. Each receives both the content string and the full `LLMContext` (which gives access to state, events, config, and the node context).

---

### Intents

Intents are handlers that run at specific points in the **node** lifecycle. They fire before and after the node executes, giving you hooks for setup, validation, auditing, and cleanup.

#### Node lifecycle hooks (in order)

| Hook            | When it fires                                           |
| --------------- | ------------------------------------------------------- |
| `PRE_DISPATCH`  | Before the node is called (setup, LLM context creation) |
| `EXECUTE`       | The `node.execute()` call itself                        |
| `POST_DISPATCH` | After execute returns (cleanup, validation)             |
| `ROUTE`         | `node.route()` call to determine next node              |

#### Implementing an intent

```python
from optorch.intents.base_intent_handler import BaseIntentHandler
from optorch.intents.intent_context import IntentContext

class ValidateOutputIntent(BaseIntentHandler):

    def should_execute(self, context: IntentContext) -> bool:
        # Conditionally skip — return False to skip this intent
        return context.state.get("validate", True)

    async def execute(self, context: IntentContext) -> dict:
        if not context.state.get("response"):
            raise ValueError("Node produced no response")
        return {"validated": True}
```

Register and reference in `nodes.yaml`:

```python
container.node_controller.intents.register("validate_output", ValidateOutputIntent())
```

```yaml
nodes:
  my_node:
    intents:
      pre_dispatch:
        - setup_context
      post_dispatch:
        - validate_output
        - store_entities
```

`IntentContext` gives each intent access to the current state, node name, phase, and the full `NodeContext`. When multiple intents are listed for a hook, they run sequentially. If any intent sets `context.skip_execution = True`, the remaining intents for that hook are skipped.

Core intents (`create_llm_context`, `cleanup_llm_context`) run automatically via the lifecycle executor — you do not register these yourself.

---

### Session Management

Sessions persist state across conversation turns. The session ID is the thread that ties multiple `orchestrator.execute()` calls together. Three backends are available:

| Backend    | `backend` value | Best for                                             |
| ---------- | --------------- | ---------------------------------------------------- |
| Memory     | `memory`        | Local dev, single-process, stateless deployments     |
| Redis      | `redis`         | Production, multi-worker, shared session state       |
| PostgreSQL | `postgres`      | Production, sessions in your main DB, full SQL audit |

Sessions are created and managed automatically. The same `session_id` across calls is what enables conversation continuity:

```python
# First turn — session created
result = await orchestrator.execute("my_node", "hello", session_id="user-123")

# Subsequent turns — state and history carried forward
result = await orchestrator.execute("my_node", "follow up", session_id="user-123")
```

The active session ID is stored in a `ContextVar` — this is the ambient session pattern. Any code that runs within the same async task can access the current session without it being threaded through every function call:

```python
# Set ambient session (done automatically by orchestrator.execute)
container.session_manager.set_current_session("user-123")

# Get current session ID from anywhere in the call stack
session_id = container.session_manager.get_id()
```

Configure in `optorch.yaml`:

```yaml
session:
  backend: memory # memory | redis | postgres
  ttl: 86400 # seconds (0 = no expiry)

  # Redis
  redis:
    host: localhost
    port: 6379
    db: 0

  # Postgres (uses main storage connection string by default)
  # postgres:
  #   table_name: sessions
```

Programmatic access from inside a node:

```python
session = self.controller.session_manager
data = await session.get_data(session_id)
await session.set_data({"key": "value"}, session_id)
exists = await session.exists(session_id)
await session.delete(session_id)
```

---

### Events

The `EventEmitter` broadcasts structured events at every stage of workflow execution. Events carry an automatic timestamp, tenant context (application ID, user ID, client ID, request ID), and the current node name extracted from state.

#### Emitting events

```python
# From a node
await self.event_emitter.emit("my.custom.event", {"detail": "value"}, state)

# From anywhere with a reference to the emitter
emitter.emit("pricing.calculated", {"amount": 9.99, "currency": "GBP"})
```

#### Listening to events

Register a listener for a specific event type:

```python
from optorch.events.listeners.base import BaseListener

class MyListener(BaseListener):
    async def on_event(self, event: dict, state=None):
        print(f"[{event['type']}] {event}")

container.event_emitter.listeners.register("pricing.calculated", MyListener())
```

Built-in listeners: `ConsoleListener` (stdout), `FileListener` (append to JSONL file), `PrometheusListener` (increments counters).

#### Event backends

Backends store and distribute events beyond the local process. Configured under `events.backends`:

```yaml
events:
  backends:
    local:
      enabled: true
      type: local # in-process listener dispatch only
    sse:
      enabled: true
      type: sse # server-sent events for browser clients
```

Kafka (via `optorch-enterprise`) adds distributed event streaming.

#### Distribution strategies

Controls how listeners are routed to backends:

```yaml
events:
  distribution:
    type: tag_based # tag_based | broadcast
```

`tag_based` routes events to backends based on tags registered on the listener. `broadcast` sends every event to all backends.

#### Event filters

Filters run on every emitted event before it reaches listeners. They can redact PII, inject context, or suppress events by type:

- `remove_pii` — redacts sensitive fields (`email`, `phone`, `ssn`, `credit_card`, `password`) in production
- `add_session_context` — injects session metadata into every event payload
- `debug_info` — adds stack frame info in development
- `event_type_pattern` — suppresses events that don't match an allowed pattern

Configure in `optorch.yaml`:

```yaml
filters:
  events:
    - type: remove_pii
      targets: [events]
      environments: [production]
    - type: add_session_context
      targets: [events]
```

#### Backend circuit breaker

Each event backend has its own `CircuitBreaker`. After `failure_threshold` consecutive delivery failures, the circuit opens and events are dropped silently for `reset_timeout` seconds before recovery is attempted. This prevents a failing Kafka broker from stalling your entire workflow:

```yaml
events:
  health:
    failure_threshold: 5
    reset_timeout: 60 # seconds
```

#### Built-in event types

`node.dispatched`, `node.executed`, `node.routed`, `llm.start`, `llm.complete`, `llm.cost`, `tool.called`, `tool.complete`, `error`, `session.start`, `session.end`, `cache.hit`, `cache.miss`

---

### History

History is the conversation context injected into each LLM call. It is multi-tier — short-term is always included; medium and long-term kick in as the conversation grows. History is cached to avoid re-fetching on every turn.

#### Memory strategies

Control how many/which messages are passed to the LLM:

| Strategy       | Description                                                            |
| -------------- | ---------------------------------------------------------------------- |
| `smart_window` | Last N messages, with configurable duplicate/noise/error filtering     |
| `token_budget` | Fill up to a token budget, selecting newest messages first             |
| `hierarchical` | Three-layer: immediate (last N) + recent batch + sampled older context |

#### Storage strategies

Control how messages are persisted between sessions:

| Strategy   | Description                                                   |
| ---------- | ------------------------------------------------------------- |
| `raw`      | Store every message verbatim                                  |
| `filtered` | Store messages that pass a filter chain                       |
| `summary`  | Summarise a batch of old messages via LLM before persisting   |
| `hybrid`   | Keep the last N messages verbatim, summarise everything older |

#### Filters

Applied to the message list before storage or injection:

| Filter      | What it removes / keeps                                |
| ----------- | ------------------------------------------------------ |
| `error`     | Messages marked as errors (keep_errors: false)         |
| `duplicate` | Messages with identical content (`by_content: true`)   |
| `noise`     | Low-value filler messages                              |
| `role`      | Messages with specific roles (e.g., remove all `tool`) |
| `length`    | Messages exceeding a character limit                   |
| `time`      | Messages outside a time window                         |
| `tool`      | Tool call/result messages                              |
| `composite` | Chains multiple filters — applied in order             |

#### Full configuration example

```yaml
history:
  cache_enabled: true
  tier_threshold: 50 # triggers medium-term tier when message count exceeds this

  short_term:
    enable_cache: true
    cache_ttl: 300 # seconds — uses Redis if cache backend is redis
    memory:
      - type: smart_window
        params:
          window_size: 20
          keep_errors: false
          remove_duplicates: true
          remove_noise: true
      # alternatives:
      # - type: token_budget
      #   params: { max_tokens: 4000 }
      # - type: hierarchical
      #   params: { immediate_count: 5, recent_count: 15, context_count: 10 }
    storage:
      - type: raw
    filters:
      - type: error
      - type: duplicate

  medium_term:
    enable_cache: true
    cache_ttl: 600
    memory:
      - type: token_budget
        params:
          max_tokens: 2000
    storage:
      - type: summary # LLM-generated summary stored instead of raw messages

  long_term:
    search:
      - type: threshold # retrieve via vector search only when similarity > threshold
        params:
          threshold: 0.75
      # alternatives: always | never | on_demand
    vector:
      provider: qdrant # qdrant | chromadb
      collection_name: optorch_history
      distance_metric: cosine # cosine | l2 | ip
      params:
        host: localhost
        port: 6333
    embedding:
      provider: ollama # ollama | openai
      model: nomic-embed-text
      params:
        base_url: http://localhost:11434
```

Long-term retrieval requires `pip install optorch[embeddings]`. The cache TTL per tier uses whichever cache backend is active (Redis or memory).

---

## Configuration

Optorch auto-discovers all `*.yaml` files in the `config/` directory. Each file is namespaced by its filename: `optorch.yaml` → accessible as `config.optorch`, `nodes.yaml` → `config.nodes`, `interactions/budget.yaml` → `config.interactions.budget`.

You can also declare additional files to merge from within `optorch.yaml` itself:

```yaml
metadata:
  directory: config/
  files:
    - nodes
    - interactions/budget
    - interactions/tariff
```

### Config Providers

The default provider reads from the filesystem (YAML files). A database provider is also available for runtime-updatable config with multi-tenancy.

| Provider         | `OPTORCH_CONFIG_PROVIDER` | Use case                                      |
| ---------------- | ------------------------- | --------------------------------------------- |
| `yaml` (default) | `yaml`                    | Filesystem YAML files, suitable for most apps |
| `database`       | `database`                | Runtime config updates, per-tenant overrides  |

Database provider requires a configured storage backend. It loads base config from YAML as a fallback during bootstrap before the DB is ready:

```bash
OPTORCH_CONFIG_PROVIDER=database
OPTORCH_CONFIG_DIR=config        # YAML fallback directory
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

Config can also be retrieved and updated at runtime via the transport layer — the `UITransportRegistry` allows external systems to push config changes to a running orchestrator.

### Hot-Reload

Config hot-reload means the orchestrator checks for config changes and applies them without restarting. Four strategies:

| Strategy | Behaviour                                         |
| -------- | ------------------------------------------------- |
| `ttl`    | Check for changes every `reload_interval` seconds |
| `always` | Check on every config access                      |
| `manual` | Only reload when explicitly triggered             |
| `none`   | Never reload — config is fixed at startup         |

```yaml
config:
  reload_strategy: ttl # ttl | always | manual | none
  reload_interval: 60 # seconds (for ttl strategy)
```

Change notifiers tell the config system _when_ to check — separate from the strategy which tells it _how_ to react:

- `file_watcher` — watches the config directory for file changes
- `redis_watcher` — subscribes to a Redis pub/sub channel for config change signals (for distributed deployments)
- `noop` — no notifications (default)

### Secrets Providers

Secrets (API keys, connection strings, passwords) are never stored in config files. A `key_prefix` in config is the **name** of the secret reference, not the value.

| Provider  | `OPTORCH_SECRET_PROVIDER` | Reads from                                |
| --------- | ------------------------- | ----------------------------------------- |
| `env`     | `env` (default)           | `os.environ` / `.env` file                |
| `aws`     | `aws`                     | AWS Secrets Manager                       |
| `vault`   | `vault`                   | HashiCorp Vault                           |
| composite | (automatic)               | Chains multiple providers, first hit wins |

```yaml
# optorch.yaml
secrets:
  provider: aws
  region: eu-west-1
```

Or via environment:

```bash
OPTORCH_SECRET_PROVIDER=aws
```

### optorch.yaml

Full annotated core config:

```yaml
# Config system
config:
  reload_strategy: ttl
  reload_interval: 60

# Auto-discover all sub-packages
auto_discover: true

# LLM client definitions
llms:
  default:
    provider: openai
    model: gpt-4o
    key_prefix: OPENAI_API_KEY
    temperature: 0.7
    max_tokens: 2048
    timeout: 30
    streaming: false
  fast:
    provider: groq
    model: llama-3.3-70b-versatile
    key_prefix: GROQ_API_KEY
    temperature: 0.3

# LLM pool (load-balanced set of clients)
llm_pools:
  resilient:
    clients: [default, fast]
    strategy: round_robin
    fallback: true

# LLM behaviour and processor config
llm:
  auto_discover: true
  lifecycle:
    processors:
      finalize:
        - class: SuggestionsGenerator
          enabled: true
          substates: [default]
        - class: CostTracker
          enabled: true
      pre_invoke:
        - class: ResponseCache
          enabled: false # enable to cache LLM responses

# Prompt templates
prompts:
  directory: prompts/

# Session backend
session:
  backend: memory # memory | redis | postgres
  ttl: 86400
  redis:
    host: localhost
    port: 6379
    db: 0

# Storage (events, history, analytics)
storage:
  store: sqlite # sqlite | timescale | mysql
  connection_string: DATABASE_URL
  pool_size: 5
  migrations_enabled: true
  retry:
    enabled: true
    max_retries: 3
  circuit_breaker:
    enabled: true
    failure_threshold: 5

# Cache
cache:
  backend: memory # memory | redis
  ttl: 300
  redis_url: REDIS_URL

# History windowing
history:
  cache_enabled: true
  tier_threshold: 50
  short_term:
    enable_cache: true
    cache_ttl: 300
    memory:
      - type: smart_window
        params:
          window_size: 20

# Events
events:
  distribution:
    type: tag_based
  backends:
    local:
      enabled: true
      type: local

# Filters
filters:
  events:
    - type: remove_pii
      targets: [events]
      environments: [production]

# Error handling
errors:
  policy:
    LLMError: log_and_raise
    ToolExecutionError: log
    ValidationError: raise
  emit_events: true

# Logging
logging:
  level: INFO
```

### nodes.yaml

Defines every node's behaviour. All fields are optional except the node key itself:

```yaml
nodes:
  my_node:
    class: MyNode # Python class name — must be registered in app_hooks
    llm: default # LLM or pool name from llms:/llm_pools:
    streaming: false # true enables SSE streaming via StandardNode

    # Tools available to this node (schemas auto-generated from type hints)
    tools:
      - search_products
      - get_pricing

    # Prompt template (relative path, no extension; loaded from prompts.directory)
    prompts:
      system: my_node_system

    # Lifecycle intent hooks
    intents:
      pre_dispatch:
        - setup_context
      post_dispatch:
        - validate_output
        - store_entities

    # Response transformers (applied in order)
    transformers:
      - extract_json
      - validate_schema

    # Routing
    routing:
      type: conditional
      on: decision
      conditions:
        approved: approval_node
        rejected: rejection_node
      default: review_node

    # Per-node retry config
    retry:
      enabled: true
      max_attempts: 3
      backoff_seconds: 1.0
      on_failure: escalate # escalate | fail | default_response

    # Per-node LLM budget
    budget:
      limit: 0.02 # USD — enforced by budget extension if installed
```

---

## Storage

`StorageManager` is the async database layer used by events, history, analytics, config (database provider), and identity. It abstracts over three backends and adds resilience, tenant filtering, and auto-migrations.

### Backends

| Backend     | `store` value | Notes                                                 |
| ----------- | ------------- | ----------------------------------------------------- |
| SQLite      | `sqlite`      | Zero config, single-file, no server                   |
| TimescaleDB | `timescale`   | PostgreSQL + time-series — recommended for production |
| MySQL       | `mysql`       | Existing MySQL/MariaDB infrastructure                 |

```yaml
storage:
  store: timescale
  connection_string: DATABASE_URL # env var name
  pool_size: 10
  pool_timeout: 30
  migrations_enabled: true
```

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/optorch
```

### Resilience

Two resilience strategies wrap every storage operation:

**Retry with exponential backoff:**

```yaml
storage:
  retry:
    enabled: true
    max_retries: 3
    initial_delay: 1.0 # seconds
    max_delay: 30.0
    exponential_base: 2.0 # delay multiplier per attempt
```

**Circuit breaker:**

```yaml
storage:
  circuit_breaker:
    enabled: true
    failure_threshold: 5 # consecutive failures before opening
    recovery_timeout: 60.0 # seconds before trying HALF_OPEN
    success_threshold: 2 # HALF_OPEN successes needed to close
```

When the circuit is open, operations fail immediately without hitting the database — preventing cascade failures under load.

### Custom Queries

The storage layer uses a query registry so you can add domain-specific queries without touching optorch core. Queries are discovered via `AutoLoader` from the path specified in config:

```yaml
storage:
  custom_queries:
    module: app.storage.queries
    auto_discover: true
```

Implement a query by subclassing `BaseQuery` and registering it. Queries receive a connection from the pool and return typed results.

### Migrations

Optorch owns its own schema entirely. The framework ships SQL migrations for all three backends (SQLite, TimescaleDB, MySQL) and runs them automatically on startup when `migrations_enabled: true`. You do not write any schema for the framework's own tables.

Migrations are split into three namespaces, each bundled inside the package and applied in version order:

**`optorch.storage`** — core workflow tables:

| Table                  | Purpose                                              |
| ---------------------- | ---------------------------------------------------- |
| `events`               | All emitted events — hypertable on TimescaleDB       |
| `interactions`         | Interactive form requests and responses — hypertable |
| `interaction_entities` | Session entity storage (structured extracted data)   |
| `node_registry`        | Runtime node metadata                                |

**`optorch.config`** — database config provider table:

| Table            | Purpose                                                  |
| ---------------- | -------------------------------------------------------- |
| `optorch_config` | Namespaced config rows with per-tenant overrides (JSONB) |

**`optorch.identity`** — full identity schema (TMF632-aligned):

| Table                      | Purpose                                              |
| -------------------------- | ---------------------------------------------------- |
| `organizations`            | Multi-tenant orgs with parent/child hierarchy        |
| `individuals`              | Users — email, password hash, status, soft-delete    |
| `organization_memberships` | User↔org membership with roles                       |
| `scim_tokens`              | Per-tenant SCIM provisioning tokens                  |
| `authorization_policies`   | Casbin DB policy storage (alternative to CSV file)   |
| `invite_tokens`            | Invitation tokens                                    |
| `reset_tokens`             | Password reset tokens                                |
| `refresh_tokens`           | JWT refresh tokens                                   |
| `user_sessions`            | Active session tracking                              |
| `casbin_policies`          | Casbin RBAC/ABAC policies (second table for adaptor) |
| `audit_logs`               | Every auth event and identity mutation               |

TimescaleDB automatically creates hypertables for `events` and `interactions` (daily chunks). The `events` table also gets column compression configured on creation — no manual TimescaleDB tuning required.

**App-specific migrations** — add your own tables alongside the framework's without touching framework code:

```python
# In app_hooks, after the container is ready
storage_manager.add_migrations("myapp", "app/storage/migrations/")
```

Your `app/storage/migrations/` directory follows the same convention:

```
app/storage/migrations/
  sqlite/
    001_products.sql
    002_orders.sql
  timescale/
    001_products.sql
    002_orders.sql
  mysql/
    001_products.sql
```

Optorch picks the right subdirectory for the active backend automatically.

For testing or specific environments, disable all migrations:

```python
storage_manager.disable_migrations()

# Or run a specific namespace manually (e.g. after the rest of the app is live)
await storage_manager.run_namespace_migrations("myapp")
```

### TimescaleDB quickstart

```bash
docker run -d --name timescaledb -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  timescale/timescaledb:latest-pg16
```

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/optorch
```

Optorch will create hypertables on first run. Time-range queries on large event volumes are orders of magnitude faster than plain PostgreSQL.

---

## Caching

`CacheManager` is a shared async cache layer used by session history, token blacklisting, policy decisions, and LLM response caching. It is available from inside nodes via `self.controller.cache_manager`.

### Backends

| Backend | `backend` value | Notes                                                   |
| ------- | --------------- | ------------------------------------------------------- |
| Memory  | `memory`        | In-process, zero setup, lost on restart                 |
| Redis   | `redis`         | Shared across workers — required for horizontal scaling |

### Configuration

```yaml
cache:
  backend: memory # memory | redis
  ttl: 300 # default TTL in seconds (null = no expiry)
  redis_url: REDIS_URL # env var name — only for redis backend
  redis_prefix: "optorch:" # key namespace prefix
  emit_events: true # emit cache.hit / cache.miss events
  emit_on_hits: false # set true to log hits (verbose)
```

```bash
REDIS_URL=redis://localhost:6379
```

The cache backend integrates automatically with the history subsystem (`cache_ttl` per tier), the session subsystem (token blacklisting), and the identity subsystem (policy caching). Switching from `memory` to `redis` in one config line makes all of these distributed without any code changes.

---

## Identity

A full identity subsystem for multi-tenant deployments. Covers authentication, authorisation, organisations, SCIM provisioning, licensing, and audit. It is fully optional — if not configured, the framework runs without any auth enforcement.

### Authentication

JWT auth is available by default. The `secret_key_secret` field is the **name** of the env var holding the signing secret:

```yaml
identity:
  authentication:
    jwt:
      algorithm: HS256
      secret_key_secret: JWT_SECRET
      issuer: optorch
      audience: optorch-api
      expires_in: 86400 # token TTL in seconds
    enable_rate_limiting: true
```

```bash
JWT_SECRET=your-secret
```

Custom authentication providers can be registered for any auth scheme:

```python
container.identity.authn.register_provider("my_provider", MyAuthProvider())
```

### Authorisation

Casbin-based RBAC and ABAC policy enforcement:

```yaml
identity:
  authorization:
    provider: casbin # casbin | opa | memory
    default_decision: Deny # fail closed — deny unless explicitly permitted
    casbin_model_path: config/casbin/model.conf
```

Policies live in `config/casbin/policy.csv`. Any request not explicitly permitted is denied by default. Custom OPA-based providers are also supported.

### SCIM provisioning

For enterprise deployments with directory sync:

```yaml
identity:
  provisioning:
    scim_enabled: true
    scim_base_path: /scim/v2
    per_tenant_tokens: true # each tenant uses its own provisioning token
```

### Licensing

```yaml
identity:
  licensing:
    mode: online # online | offline | hybrid
    online:
      validation_url: https://license.optorch.ai/validate
      cache_ttl: 3600 # cache validated licence for 1h
```

### Audit logging

```yaml
identity:
  audit:
    enable_audit_logging: true
```

Every authentication, authorisation decision, and identity mutation is logged to the storage backend.

### Bootstrap (first run)

```yaml
identity:
  bootstrap:
    create_default_user: true
    default_user:
      email: admin@example.com
      password: changeme
      role: admin
```

Remove or disable after the first run.

---

## Filters

The filter system runs on events, messages, state, and tool outputs. Filters are composable pipelines — chain them to build exactly the sanitisation you need.

### Event filters

Applied to every emitted event before it reaches listeners:

| Filter                | What it does                                                 |
| --------------------- | ------------------------------------------------------------ |
| `remove_pii`          | Redacts configured sensitive fields (`email`, `phone`, etc.) |
| `add_session_context` | Injects current session metadata into the event payload      |
| `debug_info`          | Adds stack frame info — useful in development                |
| `event_type_pattern`  | Suppresses events that don't match an allowed glob pattern   |

Configure under `filters.events` in `optorch.yaml`. Filters can be scoped to specific environments:

```yaml
filters:
  events:
    - type: remove_pii
      targets: [events]
      environments: [production, staging]
      params:
        sensitive_keys: [email, phone, ssn, credit_card, password, api_key]
    - type: add_session_context
      targets: [events]
    - type: debug_info
      targets: [events]
      environments: [development]
```

### Message filters

Applied to messages before they are sent to the LLM:

| Filter               | What it does                                               |
| -------------------- | ---------------------------------------------------------- |
| `token_limit`        | Truncates or drops messages to stay within token budget    |
| `normalize_format`   | Normalises message format inconsistencies across providers |
| `unsupported_fields` | Strips provider-unsupported fields before transmission     |

### State filters

Applied to state data before exposure or persistence:

| Filter             | What it does                                         |
| ------------------ | ---------------------------------------------------- |
| `compact_state`    | Removes large intermediate keys before serialisation |
| `redact_sensitive` | Redacts marked sensitive keys from the state dict    |

### Tool filters

Applied to tool inputs/outputs:

| Filter            | What it does                                                 |
| ----------------- | ------------------------------------------------------------ |
| `validate_params` | Validates tool call parameters against the registered schema |
| `sanitize_output` | Sanitises tool return values before passing to the LLM       |

### Writing a custom filter

```python
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter

@register_filter("my_custom_filter")
class MyFilter(BaseFilter):
    def filter(self, data: dict) -> dict | None:
        # return None to suppress the event entirely
        if data.get("internal_only"):
            return None
        return data
```

---

## Error Handling

`ErrorHandler` is the central error orchestration layer. It maps exception types to configurable actions: raise, log, emit an event, or trigger a fatal handler. Every error type has a default severity and a configurable action.

### Exception types

| Exception             | Severity | When raised                                          |
| --------------------- | -------- | ---------------------------------------------------- |
| `ConfigurationError`  | critical | Missing or invalid config                            |
| `ValidationError`     | low      | Input validation failure                             |
| `ProcessorError`      | medium   | Failure inside an LLM processor                      |
| `StateError`          | medium   | State access or mutation error                       |
| `LLMError`            | high     | LLM API failure — includes `model` and `provider`    |
| `ToolExecutionError`  | medium   | Tool call failure — includes `tool_name`             |
| `SessionError`        | high     | Session backend failure — includes `session_id`      |
| `BudgetError`         | medium   | Budget exceeded — includes `scope` and `exceeded_by` |
| `NodeContextError`    | critical | Context not properly initialised                     |
| `HTTPError`           | critical | HTTP layer error — includes `status_code`            |
| `AuthenticationError` | high     | Auth failure                                         |

### Error actions

Configure how each exception type is handled:

```yaml
errors:
  policy:
    LLMError: log_and_raise # raise | log | emit | log_and_raise | emit_and_raise | emit_and_log | fatal
    ToolExecutionError: log
    ValidationError: raise
    ConfigurationError: fatal
  emit_events: true # emit error events to EventEmitter
```

| Action           | Behaviour                                      |
| ---------------- | ---------------------------------------------- |
| `raise`          | Re-raise the exception                         |
| `log`            | Log and swallow — execution continues          |
| `emit`           | Emit an `error` event via EventEmitter         |
| `log_and_raise`  | Log then re-raise                              |
| `emit_and_raise` | Emit event then re-raise                       |
| `emit_and_log`   | Emit event and log — execution continues       |
| `fatal`          | Calls registered fatal handler, then re-raises |

Register a fatal handler for specific exception types:

```python
ErrorHandler.configure(
    fatal_handlers={
        "ConfigurationError": lambda ctx: alert_on_call(ctx.exception)
    }
)
```

Use `@error_context` decorator on node/tool methods to auto-inject `component` and `phase` into error context:

```python
from optorch.errors import error_context

@error_context(component="my_node", phase="processing")
async def process(self, context):
    ...
```

---

## Prometheus Metrics

Optorch ships a `MetricsRegistry` singleton that exposes Prometheus metrics at `/metrics`. Metrics are incremented automatically by built-in processors and middleware.

### Metrics exposed

| Metric name                             | Type      | Labels                              |
| --------------------------------------- | --------- | ----------------------------------- |
| `optorch_http_requests_total`           | Counter   | `method`, `endpoint`, `status_code` |
| `optorch_http_request_duration_seconds` | Histogram | `method`, `endpoint`                |
| `optorch_llm_requests_total`            | Counter   | `provider`, `model`, `status`       |
| `optorch_llm_request_duration_seconds`  | Histogram | `provider`, `model`                 |
| `optorch_llm_tokens_total`              | Counter   | `provider`, `model`, `token_type`   |
| `optorch_llm_cost_total`                | Counter   | `provider`, `model`, `currency`     |
| `optorch_tool_calls_total`              | Counter   | `tool_name`, `status`               |
| `optorch_tool_duration_seconds`         | Histogram | `tool_name`                         |
| `optorch_node_executions_total`         | Counter   | `node_name`, `status`               |
| `optorch_node_duration_seconds`         | Histogram | `node_name`                         |

### Enabling Prometheus

Register with the server extension:

```python
from optorch.prometheus import register_with_server
register_with_server(app)  # FastAPI app
```

Or access the registry directly:

```python
from optorch.prometheus import MetricsRegistry
metrics = MetricsRegistry()
metrics.node_executions_total.labels(node_name="my_node", status="success").inc()
```

Add `PrometheusMiddleware` for automatic HTTP metrics on every request:

```python
from optorch.prometheus import PrometheusMiddleware
app.add_middleware(PrometheusMiddleware)
```

---

## Retry & Escalation

`RetryHandler` wraps node execution with configurable retry logic. It is activated per-node via the `retry:` config block.

### Configuration

```yaml
nodes:
  my_node:
    retry:
      enabled: true
      max_attempts: 3
      backoff_seconds: 1.0 # wait between attempts
      on_failure: escalate # what to do after all attempts exhausted
```

`on_failure` values:

- `escalate` — calls the node's escalation handler (requires `RetryCoordinator`)
- `fail` — sets `error` in state and ends the workflow branch
- `default_response` — sets a configured fallback response and continues

### Custom failure types

Register custom failure type handlers to handle domain-specific failure conditions beyond simple retries:

```python
from optorch.retry import RetryHandler

class InsufficientDataHandler:
    def handle(self, state, config):
        state.set("error", "Insufficient data to complete request")
        return state

RetryHandler.register_failure_type("insufficient_data", InsufficientDataHandler())
```

### RetryCoordinator and escalation

When `on_failure: escalate`, the `RetryCoordinator` base class provides the `escalate()` method. It sets the `PENDING_PHASE` key so the coordinator knows where to resume on the next user turn:

```python
class MyCoordinator(RetryCoordinator):
    async def execute(self, state: BaseState) -> BaseState:
        pending = state.get("PENDING_PHASE")
        if pending == "research":
            # User has responded — resume from where we left off
            state = await self.call("research_node", state)

        if state.get("research_error"):
            return self.escalate(
                state=state,
                phase="research",
                template="research_failed_prompt",
                error_key="research_error",
                context_key="research_context",
            )
        return state
```

The `NEEDS_USER_INPUT` flag in state signals the server extension to return control to the user.

---

## Transport

`UITransportRegistry` manages bidirectional communication between the orchestrator and external UI components (browsers, mobile apps). Three providers: file (default, local dev), Redis pub/sub, and Kafka.

Transport is used for interactive workflows — when the orchestrator needs to pause, show a form to the user, receive input, and resume. This is the mechanism behind the `optorch-interact` extension.

### Configuration

```yaml
transport:
  active_provider: file # file | redis | kafka (null = first enabled)

  file:
    enabled: true
    dir: /tmp/optorch/transport
    probe_template: "probe_{probe_id}.json"
    response_template: "response_{probe_id}.json"

  redis:
    enabled: false
    probe_channel: optorch:transport:probe
    response_channel: optorch:transport:response
    key_prefix: "optorch:transport:"

  kafka:
    enabled: false
    probe_topic: optorch-transport-probe
    response_topic: optorch-transport-response
    consumer_group: optorch-transport-ui
```

### Using the transport registry

```python
transport = container.transport_registry
active = transport.get_active()          # get the active provider instance
providers = transport.list_available()   # list all enabled providers

# Subscribe to probe messages on all enabled providers at once
transport.subscribe_all("probes", my_callback)
```

---

## MCP Integration

Optorch connects to [Model Context Protocol](https://modelcontextprotocol.io) servers, exposing their tools to nodes via the `ToolRegistry`. MCP tools are discovered lazily on first use — no tool needs to be listed explicitly.

### Configuration

```yaml
mcp:
  auto_connect: true # connect to all registered servers on startup

  servers:
    my_tools:
      url: http://localhost:3000
      transport: sse # sse | http
      enabled: true
      timeout: 30
      auth_type: bearer # none | bearer | api_key | basic
      auth_token: MCP_TOKEN # env var name holding the token
      tools:
        specific_tool:
          enabled: false # disable a specific tool from this server
          wrapper: app.wrappers.my_fn # optional custom wrapper function path

    another_server:
      url: https://mcp.example.com
      transport: http
      auth_type: api_key
      auth_token: MCP_API_KEY
      auth_header: X-Custom-Header # override default header name
```

### How it works

1. At startup, `MCPRegistry` registers each enabled server as an `MCPClient`
2. When a node lists an MCP tool in its config (or calls `self.tool("name")`), `ToolRegistry` checks the local registry first
3. If not found locally, it queries `MCPRegistry.get_for_tool(name)` which routes to the correct server
4. The client connects (if not already connected), lists tools, wraps the target tool as a `BaseTool`, registers it locally, and executes it
5. Subsequent calls use the cached local registration — no reconnection overhead

### Accessing MCP directly

```python
from optorch.mcp import MCPRegistry

client = MCPRegistry.get("my_tools")
tools = await client.list_tools()          # [{name, description, inputSchema}]
result = await client.call_tool("my_tool", {"param": "value"})
```

---

## Embeddings & Vector Stores

The embeddings module provides a unified interface for generating text embeddings and storing/querying them in vector databases. Used by the history subsystem for long-term retrieval and available directly for custom RAG implementations.

### Embedding providers

| Provider | `provider` value | Notes                                    |
| -------- | ---------------- | ---------------------------------------- |
| Ollama   | `ollama`         | Local — requires running Ollama instance |
| OpenAI   | `openai`         | `text-embedding-3-small` and others      |

### Vector stores

| Store    | `provider` value | Notes                              |
| -------- | ---------------- | ---------------------------------- |
| Qdrant   | `qdrant`         | Recommended — fast, local or cloud |
| ChromaDB | `chromadb`       | Simple local store, good for dev   |

### Configuration (in history or standalone)

```yaml
embeddings:
  provider: ollama
  model: nomic-embed-text
  dimensions: 768
  batch_size: 32
  params:
    base_url: http://localhost:11434

vector_store:
  provider: qdrant
  collection_name: my_collection
  distance_metric: cosine # cosine | l2 | ip
  params:
    host: localhost
    port: 6333
```

### Direct usage

```python
from optorch.embeddings import EmbeddingsRegistry, VectorStoreRegistry

# Get configured embedding provider
embedder = EmbeddingsRegistry.get("default")
vectors = await embedder.embed(["text one", "text two"])

# Get configured vector store
store = VectorStoreRegistry.get("my_collection")
await store.upsert(vectors, payloads=[{"id": 1}, {"id": 2}])
results = await store.search(query_vector, top_k=5, threshold=0.75)
```

---

## Module Reference

| Module                        | Purpose                                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------- |
| `optorch.estrator`            | `Orchestrator` — entry point, container lifecycle, `create()` / `create_async()`         |
| `optorch.container`           | `ApplicationContainer` — DI container holding all services                               |
| `optorch.nodes`               | `BaseNode`, `StandardNode`, `CoordinatorNode` — node base classes                        |
| `optorch.retry`               | `RetryHandler`, `RetryCoordinator`, failure type registry                                |
| `optorch.state`               | `State`, `BaseState`, `StreamingState`, `StateFactory`                                   |
| `optorch.controller`          | `NodeController` — dispatches execution, owns all registries, route resolution           |
| `optorch.lifecycle`           | `LifecycleExecutor` — runs PRE_DISPATCH→EXECUTE→POST_DISPATCH→ROUTE hook sequence        |
| `optorch.llm`                 | `LLMManager`, `LLMRegistry`, `LLMLifecycleExecutor`, prompt manager, fragments           |
| `optorch.llm.clients`         | `OpenAIClient`, `GroqClient`, `OllamaClient` — provider implementations                  |
| `optorch.llm.processors`      | All LLM lifecycle processors — `MessageBuilder`, `ToolExecutor`, `CostTracker`, etc.     |
| `optorch.llm.lifecycle`       | `LLMContext`, hooks enum (`PRE_INVOKE`→`FINALIZE`), base processor                       |
| `optorch.config`              | `ConfigManager` — YAML/DB providers, secrets, hot-reload, runtime overrides              |
| `optorch.config.providers`    | `YamlProvider`, `DatabaseConfigProvider`                                                 |
| `optorch.config.secrets`      | `SecretProvider`, `EnvironmentSecretProvider`, composite provider                        |
| `optorch.config.reload`       | Reload strategies: `ttl`, `always`, `manual`, `none`                                     |
| `optorch.config.notifiers`    | `FileWatcher`, `RedisWatcher`, `NoOpNotifier`                                            |
| `optorch.session`             | `SessionManager`, `MemoryBackend`, `RedisBackend`, `PostgresBackend`                     |
| `optorch.events`              | `EventEmitter`, `ListenerManager`, `BackendManager`, listener base classes               |
| `optorch.events.health`       | `CircuitBreaker` per event backend                                                       |
| `optorch.events.distribution` | `TagBasedStrategy`, distribution protocol                                                |
| `optorch.registry`            | `Registry[T]` — generic key-value registry used by all subsystems                        |
| `optorch.routing`             | `RouteResolver` — static, conditional, dynamic routing; `RouteTypes` constants           |
| `optorch.history`             | `History`, `HistoryConfig`, smart window, token budget, hierarchical, storage strategies |
| `optorch.storage`             | `StorageManager`, resilience pipeline, query registry, migrations, tenant filtering      |
| `optorch.cache`               | `CacheManager` — Redis/memory via aiocache, TTL, event emission                          |
| `optorch.identity`            | `IdentityManager`, JWT auth, Casbin authz, SCIM, licensing, audit                        |
| `optorch.mcp`                 | `MCPRegistry`, `MCPClient`, `MCPServerConfig` — MCP server integration                   |
| `optorch.embeddings`          | `EmbeddingsRegistry`, `VectorStoreRegistry`, Ollama/OpenAI providers, Qdrant/ChromaDB    |
| `optorch.prometheus`          | `MetricsRegistry`, `PrometheusMiddleware`, `/metrics` route                              |
| `optorch.transport`           | `UITransportRegistry`, file/Redis/Kafka providers                                        |
| `optorch.filters`             | Event, message, state, and tool filter pipelines with composable filter chains           |
| `optorch.errors`              | Typed exceptions, `ErrorHandler` with configurable action policies                       |
| `optorch.decorators`          | `@emits` event decorator, `context_extraction` for context-aware decorators              |
| `optorch.tenant_context`      | `TenantContext` — `ContextVar`-based ambient tenant state                                |
| `optorch.loader`              | `AutoLoader` — dynamic class discovery by package and name pattern                       |
| `optorch.testing`             | Mocks, builders, snapshot assertions for node and LLM testing                            |
| `optorch.logging`             | `get_logger(__name__)`, `ContextLogger` — structured logging                             |
| `optorch.convenience`         | `invoke`, `ainvoke`, `astream` — quick LLM calls without full orchestrator               |
| `optorch.worker`              | `WorkerServer` (from enterprise extension), `WorkerHealth`                               |

---

## Convenience API

For quick LLM calls without standing up a full orchestrator. Provider is auto-detected from the model name:

```python
import optorch

# Auto-detect provider from model name (gpt-* → openai, llama-* → groq, etc.)
result = await optorch.ainvoke(model="gpt-4o-mini", message="What's 2+2?")
print(result.content)

# With explicit config
result = await optorch.ainvoke(
    model="gpt-4o",
    message="Explain recursion",
    config={"temperature": 0.3, "max_tokens": 500}
)

# Inject a pre-built client (bypasses auto-detection)
from optorch.llm.clients.openai_client import OpenAIClient
client = OpenAIClient(api_key="sk-...", model="gpt-4o")
result = await optorch.ainvoke(message="Hello", client=client)

# Streaming
async for chunk in optorch.astream(model="gpt-4o", message="Tell me a story"):
    print(chunk.content, end="", flush=True)

# Sync wrapper (blocks the thread)
result = optorch.invoke(model="gpt-4o-mini", message="Quick answer")
```

The convenience API reads API keys from the same environment variables as the full framework. There is no config file required.

---

## Testing

Optorch ships a `testing` module with mocks, builders, and assertion helpers:

```python
from optorch.testing.mocks import MockLLMClient
from optorch.testing.builders import StateBuilder
from optorch.testing.assertions import assert_state_contains

# Build a pre-populated test state
state = (
    StateBuilder()
    .with_message("user", "test input")
    .with_data({"session_id": "test-123", "name": "Alice"})
    .build()
)

# Mock LLM client — returns a fixed response without calling any API
client = MockLLMClient(response="mocked response")

# Assert state contains expected values after node execution
my_node = MyNode("my_node", config={})
result = await my_node.execute(state)
assert_state_contains(result, {"response": "expected value"})
```

Run the test suite:

```bash
pytest tests/
```

With coverage:

```bash
pytest tests/ --cov=optorch --cov-report=html
open htmlcov/index.html
```

---

## Extensions

Optorch is intentionally minimal. Additional capabilities are separate packages, each with `install_requires=["optorch>=0.1.0"]`:

| Package                 | Description                                                                        |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `optorch-server`        | FastAPI server with SSE streaming, health checks, multi-tenant routing, CORS       |
| `optorch-analytics`     | Read-only observability API — cost by node/model, evaluation pipelines, dashboards |
| `optorch-budget`        | Cost tracking and enforcement at session/node/phase/call scope with UI approval    |
| `optorch-interact`      | Interactive forms — Pydantic models rendered as UI prompts, distributed wait       |
| `optorch-enterprise`    | Kafka workers, Kinesis event streaming, horizontal scaling                         |
| `optorch-notifications` | Multi-channel notifications — email, Slack, Discord, webhook, SMS                  |

Extensions register themselves via `container.extension_registry.register(name, cleanup=..., **metadata)` and clean up after themselves on shutdown.

---

## Licence

Proprietary. Copyright © Chris Churchill. All rights reserved.
