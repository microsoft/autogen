import pytest
from autogen_agentchat.optimize import list_backends, compile
from autogen_agentchat.optimize._backend import BaseBackend


def test_backend_registry():
    """Test that the backend registry works."""
    # Should start with no backends if DSPy not available
    backends_before = list_backends()
    
    # Create a dummy backend for testing
    class DummyBackend(BaseBackend):
        name = "dummy"
        
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {"optimizer": "dummy", "status": "test"}
    
    # Should now have the dummy backend
    backends_after = list_backends()
    assert "dummy" in backends_after
    assert len(backends_after) == len(backends_before) + 1


def test_backend_not_found():
    """Test error handling for unknown backend."""
    from autogen_agentchat.optimize._backend import get_backend
    
    with pytest.raises(ValueError, match="Unknown backend 'nonexistent'"):
        get_backend("nonexistent")


def test_compile_with_dummy_backend():
    """Test compile function with dummy backend."""
    # Create a dummy backend
    class TestBackend(BaseBackend):
        name = "test"
        
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {"optimizer": "test", "result": "success"}
    
    # Create a dummy agent
    class DummyAgent:
        def __init__(self):
            self.system_message = "You are a helpful assistant."
    
    agent = DummyAgent()
    trainset = []
    metric = lambda x, y: True
    
    optimized_agent, report = compile(agent, trainset, metric, backend="test")
    
    assert optimized_agent is agent
    assert report["optimizer"] == "test"
    assert report["result"] == "success"


def test_dspy_backend_unavailable():
    """Test that DSPy backend is properly handled when DSPy is not available."""
    backends = list_backends()
    
    # DSPy backend should not be available if DSPy is not installed
    if "dspy" not in backends:
        # This is expected if DSPy is not installed
        with pytest.raises(ValueError, match="Unknown backend 'dspy'"):
            compile(None, [], lambda x, y: True, backend="dspy")
    else:
        # If DSPy is available, test should pass
        pytest.skip("DSPy is available, skipping unavailable test")