import pytest
from unittest.mock import Mock
from autogen_agentchat.optimize import list_backends, compile
from autogen_agentchat.optimize._backend import BaseBackend, get_backend


def test_backend_registry():
    """Test that the backend registry works."""
    # Get initial backends (might include dspy if loaded)
    backends_before = set(list_backends())
    
    # Create a dummy backend for testing
    class DummyBackend(BaseBackend):
        name = "dummy"
        
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {"optimizer": "dummy", "status": "test"}
    
    # Should now have the dummy backend
    backends_after = set(list_backends())
    assert "dummy" in backends_after
    assert backends_after == backends_before.union({"dummy"})


def test_backend_not_found():
    """Test error handling for unknown backend."""
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


def test_dspy_backend_registration():
    """Test that DSPy backend is properly registered when module is imported."""
    # Import the DSPy backend to register it
    from autogen_ext.optimize.dspy import DSPyBackend
    
    backends = list_backends()
    assert "dspy" in backends


def test_dspy_backend_unavailable():
    """Test that DSPy backend gracefully handles missing DSPy dependency."""
    from autogen_ext.optimize.dspy import DSPyBackend
    
    class DummyAgent:
        def __init__(self):
            self.system_message = "You are helpful"
            self._model_client = Mock()

    agent = DummyAgent()
    trainset = []
    metric = lambda x, y: True
    
    backend = DSPyBackend()
    
    # Should raise ImportError about missing DSPy
    with pytest.raises(ImportError, match="DSPy is required for optimization"):
        backend.compile(agent, trainset, metric)


def test_dspy_backend_missing_model_client():
    """Test DSPy backend error handling for missing model client."""
    from autogen_ext.optimize.dspy import DSPyBackend
    
    class DummyAgent:
        def __init__(self):
            self.system_message = "You are helpful"
            # No model_client attribute
    
    agent = DummyAgent()
    trainset = []
    metric = lambda x, y: True
    
    backend = DSPyBackend()
    
    # Should raise ValueError about missing model client
    with pytest.raises(ValueError, match="Could not find model_client"):
        backend.compile(agent, trainset, metric)


def test_compile_function_with_kwargs():
    """Test that compile function forwards kwargs to backend."""
    class KwargsTestBackend(BaseBackend):
        name = "kwargs_test"
        
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {"received_kwargs": kwargs}
    
    class DummyAgent:
        pass
    
    agent = DummyAgent()
    trainset = []
    metric = lambda x, y: True
    
    # Pass some kwargs
    test_kwargs = {"optimizer_name": "MIPROv2", "max_steps": 10}
    optimized_agent, report = compile(
        agent, trainset, metric, 
        backend="kwargs_test", 
        **test_kwargs
    )
    
    assert report["received_kwargs"] == test_kwargs


def test_list_backends_returns_sorted():
    """Test that list_backends returns a sorted list."""
    # Create multiple backends
    class BackendZ(BaseBackend):
        name = "z_backend"
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {}
    
    class BackendA(BaseBackend):
        name = "a_backend"
        def compile(self, agent, trainset, metric, **kwargs):
            return agent, {}
    
    backends = list_backends()
    
    # Should be sorted alphabetically
    assert backends == sorted(backends)
    assert "a_backend" in backends
    assert "z_backend" in backends