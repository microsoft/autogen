# AutoGen Services

## Overview

Each AutoGen agent system has one or more Agent Workers and a set of services for managing/supporting the agents. The services and workers can all be hosted in the same process or in a distributed system.  When in the same process communication and event delivery is in-memory. When distributed, workers communicate with the service over gRPC. In all cases, events are packaged as CloudEvents. There are multiple options for the backend services:

- In-Memory: the Agent Workers and Services are all hosted in the same process and communicate over in-memory channels. Available for python and .NET.
- Python only: Agent workers communicate with a python hosted service that implements an in-memory message bus and agent registry.
- Micrososft Orleans: a distributed actor system that can host the services and workers, enables distributed state with persistent storage, can leverage multiple event bus types, and cross-language agent communication.
- *Roadmap: support for other languages distributed systems such as dapr or Akka.*

The Services in the system include:

- Worker: Hosts the Agents and is a client to the Gateway
- Gateway:
-- RPC gateway for the other services APIs
-- Provides an RPC bridge between the workers and the Event Bus
-- Message Session state (track message queues/delivery)
- Registry: keeps track of the {agents:agent types}:{Subscription/Topics} in the system and which events they can handle
-- *Roadmap: add lookup api in gateway*
- AgentState: persistent state for agents
- Routing: delivers events to agents based on their subscriptions+topics
-- *Roadmap: add subscription management APIs*
- *Roadmap: Management APIs for the Agent System*
- *Roadmap: Scheduling: manages placement of agents*
- *Roadmap: Discovery: allows discovery of agents and services*
