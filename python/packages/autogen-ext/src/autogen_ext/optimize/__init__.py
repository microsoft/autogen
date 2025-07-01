# Optimization backends for AutoGen agents

# Try to import DSPy backend to register it
try:
    from .dspy import DSPyBackend  # noqa: F401
except ImportError:
    # DSPy not available, skip registration
    pass