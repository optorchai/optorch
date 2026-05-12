import pytest
from optorch.testing.mocks import MockLLMProvider, EventCapture, MockStateContainer, MockMCPClient
from optorch.testing.builders import StateBuilder


@pytest.fixture(scope="session", autouse=True)
def register_budget_adapters():
    """register budget adapters globally for all tests"""
    from extensions.budget.registries import BudgetScopeRegistry, BudgetEnforcementRegistry
    from extensions.budget.scopes.llm_call import LLMCallScope
    from extensions.budget.scopes.session import SessionScope
    from extensions.budget.scopes.http_request import HTTPRequestScope
    from extensions.budget.scopes.node import NodeScope
    from extensions.budget.scopes.phase import PhaseScope
    from extensions.budget.enforcement.block import BlockEnforcement
    from extensions.budget.enforcement.warn import WarnEnforcement
    from extensions.budget.enforcement.interactive import InteractiveEnforcement
    
    # register built-in adapters
    BudgetScopeRegistry.register("llm_call", LLMCallScope)
    BudgetScopeRegistry.register("session", SessionScope)
    BudgetScopeRegistry.register("http_request", HTTPRequestScope)
    BudgetScopeRegistry.register("node", NodeScope)
    BudgetScopeRegistry.register("phase", PhaseScope)
    
    BudgetEnforcementRegistry.register("block", BlockEnforcement)
    BudgetEnforcementRegistry.register("warn", WarnEnforcement)
    BudgetEnforcementRegistry.register("interactive", InteractiveEnforcement)
    
    yield


@pytest.fixture
def mock_llm():
    provider = MockLLMProvider()
    yield provider
    provider.reset()


@pytest.fixture
def event_capture():
    capture = EventCapture()
    yield capture
    capture.stop()
    capture.clear()


@pytest.fixture
def mock_state():
    return MockStateContainer()


@pytest.fixture
def state_builder():
    return StateBuilder()


@pytest.fixture
def mock_mcp():
    return MockMCPClient()


@pytest.fixture
def mock_node_context():
    """create minimal NodeContext for testing"""
    from unittest.mock import Mock
    context = Mock()
    context.controller = Mock()
    context.events = Mock()
    context.sessions = Mock()
    context.history = Mock()
    context.cache = Mock()
    return context

