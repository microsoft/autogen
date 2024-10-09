# FAQs

## How do I get the underlying agent instance?

Agents might be distributed across multiple machines, so the underlying agent instance is intentionally discouraged from being accessed. If the agent is definitely running on the same machine, you can access the agent instance by calling {py:meth}`autogen_core.base.AgentRuntime.try_get_underlying_agent_instance` on the `AgentRuntime`. If the agent is not available this will throw an exception.

## How do I call call a function on an agent?

Since the instance itself is not accessible, you can't call a function on an agent directly. Instead, you should create a type to represent the function call and its arguments, and then send that message to the agent. Then in the agent, create a handler for that message type and implement the required logic. This also supports returning a response to the caller.

This allows your agent to work in a distributed environment a well as a local one.

## Why do I need to use a factory to register an agent?

An {py:class}`autogen_core.base.AgentId` is composed of a `type` and a `key`. The type corresponds to the factory that created the agent, and the key is a runtime, data dependent key for this instance.

The key can correspond to a user id, a session id, or could just be "default" if you don't need to differentiate between instances. Each unique key will create a new instance of the agent, based on the factory provided. This allows the system to automatically scale to different instances of the same agent, and to manage the lifecycle of each instance independently based on how you choose to handle keys in your application.
