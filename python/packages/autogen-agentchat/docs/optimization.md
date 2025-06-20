# AutoGen Agent Optimizer

The AutoGen Agent Optimizer provides a unified interface for optimizing AutoGen agents using various optimization backends. This allows you to improve agent performance by automatically tuning system messages and tool descriptions based on training data.

## Installation

The base optimization interface is included with `autogen-agentchat`. To use the DSPy backend, you'll also need to install DSPy:

```bash
pip install autogen-ext[dspy]
# or directly
pip install dspy
```

## Basic Usage

```python
from autogen_agentchat.optimize import compile, list_backends

# Check available backends
print("Available backends:", list_backends())

# Optimize an agent
optimized_agent, report = compile(
    agent=my_agent,
    trainset=training_examples,
    metric=evaluation_function,
    backend="dspy",
    optimizer_name="MIPROv2",
    optimizer_kwargs={"max_steps": 16}
)
```

## Interface

### `compile(agent, trainset, metric, *, backend="dspy", **kwargs)`

Optimizes an AutoGen agent by tuning its system message and tool descriptions.

**Parameters:**
- `agent`: Any AutoGen agent (e.g., AssistantAgent)
- `trainset`: Iterable of training examples (DSPy Examples or backend-specific format)
- `metric`: Evaluation function `(gold, pred) → float | bool`
- `backend`: Name of optimization backend (default: "dspy")
- `**kwargs`: Additional parameters passed to the backend

**Returns:**
- `(optimized_agent, report)`: Tuple of the optimized agent and optimization report

### `list_backends()`

Returns a list of available optimization backends.

## Backends

### DSPy Backend

The DSPy backend uses the DSPy optimization framework to improve agent prompts.

**Supported optimizers:**
- SIMBA (default)
- MIPROv2
- And any other DSPy optimizer

**Backend-specific parameters:**
- `lm_client`: Language model client (defaults to agent's model client)
- `optimizer_name`: Name of DSPy optimizer (default: "SIMBA")
- `optimizer_kwargs`: Additional optimizer parameters

## Example

See `examples/optimization_demo.py` for a complete example demonstrating the interface.

## Adding New Backends

To add a new optimization backend:

1. Create a class inheriting from `BaseBackend`
2. Set the `name` class attribute  
3. Implement the `compile()` method
4. The backend will be automatically registered when imported

```python
from autogen_agentchat.optimize._backend import BaseBackend

class MyBackend(BaseBackend):
    name = "my_backend"
    
    def compile(self, agent, trainset, metric, **kwargs):
        # Your optimization logic here
        return optimized_agent, report
```