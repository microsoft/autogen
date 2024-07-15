# AGNext (temp name) - (aka codename Starfleet) Agents Framework SDK

Starfleet is a framework for developing intelligent applications using AI Agents patterns.

Starfleet offers an easy way to quickly build event-driven, distributed, scalable, resilient AI agent systems. Agents are developed by using the [Actor model](https://en.wikipedia.org/wiki/Actor_model). Each agent has events that it cares about and can process. Each agent may also emit events.

You can build and run your agent system locally and easily move to a distributed system in the cloud when you are ready.

The SDK comes with built-in agents that you can use as starting points. You can also use your own agents built from scratch, and use the Starfleet SDK to integrate them with other systems or to scale them into the cloud.

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

You may want to leverage more prescriptive agent behavior contracts, and Starfleet also includes base agents that implement different approaches to agent behavior, including layering request/response patterns on top of the event-driven model. For an example of this see the ChatAgents in the Python examples.

## Languages

- [Python README](https://github.com/microsoft/agnext/tree/main/python/README.md) for how to develop and test the Python package.
- [Python Documentation](http://microsoft.github.io/agnext) for the core concepts and API reference.
- [Python Examples](https://github.com/microsoft/agnext/tree/main/python/examples) for examples of how to use the Python package and multi-agent patterns.
- [.NET](https://github.com/microsoft/agnext/tree/main/dotnet)
