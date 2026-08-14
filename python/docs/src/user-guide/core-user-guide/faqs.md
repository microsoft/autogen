# FAQs

## How do I get the underlying agent instance?

Agents might be distributed across multiple machines, so the underlying agent instance is intentionally discouraged from being accessed. If the agent is definitely running on the same machine, you can access the agent instance by calling {py:meth}`autogen_core.AgentRuntime.try_get_underlying_agent_instance` on the `AgentRuntime`. If the agent is not available this will throw an exception.

## How do I call call a function on an agent?

Since the instance itself is not accessible, you can't call a function on an agent directly. Instead, you should create a type to represent the function call and its arguments, and then send that message to the agent. Then in the agent, create a handler for that message type and implement the required logic. This also supports returning a response to the caller.

This allows your agent to work in a distributed environment a well as a local one.

## Why do I need to use a factory to register an agent?

An {py:class}`autogen_core.AgentId` is composed of a `type` and a `key`. The type corresponds to the factory that created the agent, and the key is a runtime, data dependent key for this instance.

The key can correspond to a user id, a session id, or could just be "default" if you don't need to differentiate between instances. Each unique key will create a new instance of the agent, based on the factory provided. This allows the system to automatically scale to different instances of the same agent, and to manage the lifecycle of each instance independently based on how you choose to handle keys in your application.

## How do I increase the GRPC message size?

If you need to provide custom gRPC options, such as overriding the `max_send_message_length` and `max_receive_message_length`, you can define an `extra_grpc_config` variable and pass it to both the `GrpcWorkerAgentRuntimeHost` and `GrpcWorkerAgentRuntime` instances.

```python
# Define custom gRPC options
extra_grpc_config = [
    ("grpc.max_send_message_length", new_max_size),
    ("grpc.max_receive_message_length", new_max_size),
]

# Create instances of GrpcWorkerAgentRuntimeHost and GrpcWorkerAgentRuntime with the custom gRPC options

host = GrpcWorkerAgentRuntimeHost(address=host_address, extra_grpc_config=extra_grpc_config)
worker1 = GrpcWorkerAgentRuntime(host_address=host_address, extra_grpc_config=extra_grpc_config)
```

**Note**: When `GrpcWorkerAgentRuntime` creates a host connection for the clients, it uses `DEFAULT_GRPC_CONFIG` from `HostConnection` class as default set of values which will can be overriden if you pass parameters with the same name using `extra_grpc_config`.

## What are model capabilities and how do I specify them?

Model capabilites are additional capabilities an LLM may have beyond the standard natural language features. There are currently 3 additional capabilities that can be specified within Autogen

- vision: The model is capable of processing and interpreting image data.
- function_calling: The model has the capacity to accept function descriptions; such as the function name, purpose, input parameters, etc; and can respond with an appropriate function to call including any necessary parameters.
- json_output: The model is capable of outputting responses to conform with a specified json format.

Model capabilities can be passed into a model, which will override the default definitions. These capabilities will not affect what the underlying model is actually capable of, but will allow or disallow behaviors associated with them. This is particularly useful when [using local LLMs](cookbook/local-llms-ollama-litellm.ipynb).

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient

client = OpenAIChatCompletionClient(
    model="gpt-4o",
    api_key="YourApiKey",
    model_capabilities={
        "vision": True,
        "function_calling": False,
        "json_output": False,
    }
)
```
