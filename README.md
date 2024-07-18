# AGNext - Codename Starfleet - Agents Framework SDK

Starfleet (*formerly AGNext - product name TBD*) is a OSS framework for developing intelligent applications using AI Agents patterns.

Starfleet offers an easy way to quickly build event-driven, distributed, scalable, resilient AI agent systems. Agents are developed by using the [Actor model](https://en.wikipedia.org/wiki/Actor_model). Each agent has events that it cares about and can process. Each agent may also emit events.

You can build and run your agent system locally and easily move to a distributed system in the cloud when you are ready.

The SDK comes with built-in agents that you can use as starting points. You can also use your own agents built from scratch, and use the Starfleet SDK to integrate them with other systems or to scale them into the cloud.

## Key Aspects of Starfleet

- Event-driven: Agents act by handling & emitting events (chatrooms are just a special case of an event-driven system)
- Scalable & Distributed: Enable complex scenarios with networks of agents across org boundaries
- Modular, extensible & highly customizable: E.g. custom agents, memory as a service, tools registry, model library
- x-lang support: Python & Dotnet interoperating agents today, others coming soon
- Observable, traceable & debuggable

## Developing with Starfleet

To build an agent system in Starfleet developers focus on understanding the overall workflow and mapping that flow into various AI agents.

- Identify the workflow/goals of the system
- Break Components of the workflow down into Agents
  - Gather prompts, data sources, skills (external APIs)
  - Model the Events that each Agent Handles
  - Each event is a function that can change state, call models, access memory, call external tools, emit other events
  - Each function can flow data to/from other systems
  - Model any Events that the agent Emits
- Build Evaluation for the Workflow/Agent System (are there specific events that demonstrate successful completion, etc.)
- Build APIs/Control code for invoking the Agent System
- You can test and run your agent system locally
- When you are ready you can use 'azd' or GH Actions to deploy your agent system to the cloud

You may want to leverage more prescriptive agent behavior contracts, and in addition to the pub/sub model agents Starfleet also offers request/response message system base agents that implement different approaches to agent behavior, including layering request/response patterns on top of the event-driven model. For an example of this see the ChatAgents in the Python examples.

## Getting Started

We are admittedly in the early stages of development, but we are excited to share our progress with you. We are looking for feedback and contributions to help shape the future of this project. Your best place to start is in the samples directories for [python](https://github.com/microsoft/agnext/tree/main/python/samples) and [.NET](https://github.com/microsoft/agnext/tree/main/dotnet/samples).

- [Python README](https://github.com/microsoft/agnext/tree/main/python/README.md) for how to develop and test the Python package.
- [Python Documentation](http://microsoft.github.io/agnext) for the core concepts and API reference.
- [Python Examples](https://github.com/microsoft/agnext/tree/main/python/samples) for examples of how to use the Python package and multi-agent patterns.
- [.NET](https://github.com/microsoft/agnext/tree/main/dotnet)
- [.NET Examples](https://github.com/microsoft/agnext/tree/main/dotnet/samples)
