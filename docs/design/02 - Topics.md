# Topics

This document describes the semantics and components of publishing messages and subscribing to topics.

## Overview

Topics are used as the primitive to manage which agents receive a given published message. Agents subscribe to topics. There is an application defined mapping from topic to agent instance.

These concepts intentionally map to the [CloudEvents](https://cloudevents.io/) specification. This allows for easy integration with existing systems and tools.

### Non-goals

This document does not specify RPC/direct messaging

## Identifiers

A topic is identified by two components (called a `TopicId`):

- [`type`](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#type) - represents the type of event that occurs, this is static and defined in code
  - SHOULD use reverse domain name notation to avoid naming conflicts. For example: `com.example.my-topic`.
  - Allowed values MUST match the regex: `^[\w\-\.\:\=]+\Z`
  - Notably, this is the same as agent type with the addition of `=` and `:` characters
- [`source`](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md#source-1) - represents where the event originated from, this is dynamic and based on the message itself
  - SHOULD be a URI

Agent instances are identified by two components (called an `AgentId`):

- `type` - represents the type of agent, this is static and defined in code
  - Allowed values MUST match the regex: `^[\w\-\.]+\Z`
- `key` - represents the instance of the agent type for the key
  - SHOULD be a URI

For example: `GraphicDesigner:1234`

## Subscriptions

Subscriptions define which agents receive messages published to a topic. Subscriptions are dynamic and can be added or removed at any time.

A subscription defines two things:

- Matcher func of type `TopicId -> bool`, telling us "does this subscription match this topic"
- Mapper func of type `TopicId -> AgentId`, telling us "given this subscription matches this topic, which agent does it map to"

These functions MUST be be free of side effects such that the evaluation can be cached.

### Agent instance creation

If a message is received on a topic that maps to an agent that does not yet exist the runtime will instantiate an agent to fullfil the request.

## Message types

Agents are able to handle certain types of messages. This is an internal detail of an agent's implementation. All agents in a channel will receive all messages, but will ignore messages that it cannot handle.

> [!NOTE]
> This might be revisited based on scaling and performance considerations.

## Well known topic types

Agents should subscribe via a prefix subscription to the `{AgentType}:` topic as a direct message channel for the agent type.

For this subscription source should map directly to agent key.

This subscription will therefore receive all events for the following well known topics:

- `{AgentType}:` - General purpose direct messages. These should be routed to the appropriate message handler.
- `{AgentType}:rpc_request={RequesterAgentType}` - RPC request messages. These should be routed to the appropriate RPC handler, and RequesterAgentType used to publish the response
- `{AgentType}:rpc_response={RequestId}` - RPC response messages. These should be routed back to the response future of the caller.
- `{AgentType}:error={RequestId}` - Error message that corresponds to the given request.
