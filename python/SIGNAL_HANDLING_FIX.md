# Azure Container Apps Signal Handling Fix

## Issue Summary

**GitHub Issue**: #6611 - "The Autogen core distributed group chat sample not working when app deployed to Azure Container App"

**Problem**: The `stop_when_signal()` method in AutoGen's gRPC runtime host was not working properly in Azure Container Apps and other container environments. The application would exit immediately instead of waiting for signals, causing the "RuntimeError: Host runtime is not started" error.

## Root Cause Analysis

The issue was caused by limitations of Python's `asyncio.loop.add_signal_handler()` when running in container environments:

1. **Container PID 1 Issues**: When Python runs as PID 1 in containers, signal handling behaves differently
2. **Azure Container Apps Environment**: Signal delivery may not work as expected in this environment
3. **Limited Signal Handling**: The original implementation only used `loop.add_signal_handler()` which has known limitations in containers

## Solution Implementation

### 1. Container Environment Detection

Added utility functions to detect container environments:

```python
def _is_running_in_container() -> bool:
    """Detect if running in a container environment."""
    container_indicators = [
        os.path.exists("/.dockerenv"),  # Docker
        os.path.exists("/var/run/secrets/kubernetes.io"),  # Kubernetes
        os.environ.get("CONTAINER_APP_NAME") is not None,  # Azure Container Apps
        os.environ.get("CONTAINER") == "true",  # Generic
        os.environ.get("DOCKER_CONTAINER") == "true",  # Generic
    ]
    return any(container_indicators)

def _is_pid_1() -> bool:
    """Check if running as PID 1."""
    return os.getpid() == 1
```

### 2. Robust Signal Handling

Implemented a multi-strategy signal handling approach:

```python
async def _robust_signal_handler(
    shutdown_event: asyncio.Event, 
    signals: Sequence[signal.Signals] = (signal.SIGTERM, signal.SIGINT)
) -> None:
    """
    Robust signal handling with multiple fallback strategies:
    1. asyncio.loop.add_signal_handler (standard approach)
    2. signal.signal with threading (fallback for containers)
    3. Periodic signal checking (fallback for PID 1 scenarios)
    """
```

**Strategy 1**: Standard `asyncio.loop.add_signal_handler()` - works in most cases
**Strategy 2**: `signal.signal()` with threading - works in containers
**Strategy 3**: Periodic signal checking - last resort for PID 1 scenarios

### 3. Updated Methods

Modified both `GrpcWorkerAgentRuntimeHost.stop_when_signal()` and `GrpcWorkerAgentRuntime.stop_when_signal()` to:

- Detect container environments
- Use robust signal handling
- Provide detailed logging for debugging
- Maintain backward compatibility

## Files Modified

1. **`python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime_host.py`**
   - Added container detection functions
   - Added robust signal handler
   - Updated `stop_when_signal()` method

2. **`python/packages/autogen-ext/src/autogen_ext/runtimes/grpc/_worker_runtime.py`**
   - Added same container detection and signal handling
   - Updated `stop_when_signal()` method

3. **`python/packages/autogen-ext/tests/test_worker_runtime.py`**
   - Added tests for container detection
   - Added tests for signal handling

4. **`python/samples/core_distributed-group-chat/run_host.py`**
   - Updated to demonstrate the fix
   - Added logging for debugging

## Testing

### Unit Tests
- `test_container_environment_detection()`: Tests environment detection functions
- `test_robust_signal_handling()`: Tests signal handling for host runtime
- `test_worker_runtime_signal_handling()`: Tests signal handling for worker runtime

### Manual Testing
- Created `python/test_signal_handling.py` for manual testing
- Tests both container detection and signal handling

## Deployment Benefits

### Azure Container Apps
- ✅ Properly handles SIGTERM signals sent by Azure Container Apps
- ✅ Works with container lifecycle management
- ✅ Supports graceful shutdown

### Docker
- ✅ Works when running as PID 1
- ✅ Handles Docker stop commands properly
- ✅ Supports multi-stage signal handling

### Kubernetes
- ✅ Handles pod termination signals
- ✅ Works with rolling updates
- ✅ Supports graceful pod shutdown

### Local Development
- ✅ Maintains backward compatibility
- ✅ Works on Windows, Linux, and macOS
- ✅ No performance impact

## Usage Example

```python
import asyncio
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost

async def main():
    host = GrpcWorkerAgentRuntimeHost(address="0.0.0.0:50051")
    host.start()
    
    # This now works reliably in Azure Container Apps
    await host.stop_when_signal()

if __name__ == "__main__":
    asyncio.run(main())
```

## Backward Compatibility

- ✅ No breaking changes to existing APIs
- ✅ Same method signatures
- ✅ Graceful fallback to original behavior if needed
- ✅ All existing tests continue to pass

## Documentation Updates

Added version annotations following project guidelines:

```python
.. versionadded:: v0.4.1
   Added container environment detection for improved signal handling.

.. versionchanged:: v0.4.1
   Improved signal handling for container environments including Azure Container Apps.
```

## Quality Assurance

- ✅ All code formatting checks pass (`poe format`)
- ✅ All linting checks pass (`poe lint`)
- ✅ All type checking passes (`mypy`)
- ✅ All existing tests continue to pass
- ✅ New tests added for the functionality

This fix resolves the Azure Container Apps deployment issue while maintaining full backward compatibility and improving signal handling across all container environments.
