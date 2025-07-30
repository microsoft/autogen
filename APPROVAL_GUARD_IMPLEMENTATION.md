# ApprovalGuard Integration for AutoGen

## Overview

This implementation adds ApprovalGuard functionality from magentic-ui to AutoGen's `autogen-agentchat` package, providing approval-based control over code execution in `CodeExecutorAgent` and `MagenticOne` team.

## Files Added

### Core Implementation
- `python/packages/autogen-agentchat/src/autogen_agentchat/approval_guard.py` - Main ApprovalGuard class
- `python/packages/autogen-agentchat/src/autogen_agentchat/guarded_action.py` - Supporting guarded action framework
- `python/packages/autogen-agentchat/src/autogen_agentchat/input_func.py` - Input function type definitions

### Tests
- `python/packages/autogen-agentchat/tests/test_approval_guard.py` - Unit tests for ApprovalGuard
- `python/packages/autogen-agentchat/tests/test_code_executor_agent_approval.py` - Integration tests

### Examples
- `examples/approval_guard_example.py` - Comprehensive usage examples
- `examples/simple_approval_demo.py` - Simple demonstration of policies

## Files Modified

### Core Integration
- `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_code_executor_agent.py` - Added approval_guard parameter and integration logic
- `python/packages/autogen-ext/src/autogen_ext/teams/magentic_one.py` - Added approval_guard parameter pass-through

## Key Features

### Approval Policies
- **"always"**: Always require approval for code execution
- **"never"**: Never require approval (bypass approval system)
- **"auto-conservative"**: Use LLM to determine approval need (conservative bias)
- **"auto-permissive"**: Use LLM to determine approval need (permissive bias)

### Input Functions
- Support for both sync and async input functions
- Configurable default approval behavior
- JSON response parsing for advanced approval workflows

### Integration Points
- `CodeExecutorAgent`: Added `approval_guard` parameter to constructor
- `MagenticOne`: Added `approval_guard` parameter that passes through to internal `CodeExecutorAgent`

## Usage Examples

### Basic Usage
```python
from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig
from autogen_agentchat.agents import CodeExecutorAgent

# Create approval guard with always policy
approval_guard = ApprovalGuard(
    input_func=my_input_function,
    config=ApprovalConfig(approval_policy="always")
)

# Create agent with approval guard
agent = CodeExecutorAgent(
    name="executor",
    code_executor=my_code_executor,
    approval_guard=approval_guard
)
```

### With MagenticOne
```python
from autogen_ext.teams.magentic_one import MagenticOne

# Create team with approval guard
team = MagenticOne(
    client=my_client,
    approval_guard=approval_guard
)
```

## Error Handling
- `ApprovalDeniedError`: Raised when user denies approval for code execution
- Graceful fallback to default approval when input functions fail

## Testing
- Comprehensive unit tests covering all approval policies
- Integration tests verifying CodeExecutorAgent workflow
- Standalone demonstration of core logic
- All syntax validation passes

## Compatibility
- Fully backward compatible - approval_guard parameter is optional
- No breaking changes to existing APIs
- Follows existing AutoGen patterns and conventions

This implementation provides a robust approval framework that maintains security and user control over code execution while preserving the flexibility and power of AutoGen's agent system.