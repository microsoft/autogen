# Programming Model

Understanding your workflow and mapping it to agents is the key to building an agent system in Starfleet.

The programming model is basically publish-subscribe. Agents subscribe to events they care about and also can publish events that other agents may care about. Agents may also have additonal assets such as Memory, prompts, data sources, and skills (external APIs).

## Events Delivered as CloudEvents

Each event in the system is defined using the [CloudEvents Specification](https://cloudevents.io/). This allows for a common event format that can be used across different systems and languages.  In CloudEvents, each event has a Context Attributes that must unique *id* (eg a UUID) a *source* (a unique urn or path), a *type* (the namespace of the event - prefixed with a reverse-DNS name. The prefixed domain dictates the organization which defines the semantics of this event type: e.g *com.github.pull_request.opened* or
*com.example.object.deleted.v2*), and optionally fields describing the data schema/content-type or extensions.

## Event Handlers

Each agent has a set of event handlers, that are bound to a specific match against a CloudEvents *type*. Event Handlers could match against an exact type or match for a pattern of events of a particular level in the type heirarchy (eg: *com.Microsoft.AutoGen.Agents.System.\** for all Events in the *System* namespace) Each event handler is a function that can change state, call models, access memory, call external tools, emit other events, and flow data to/from other systems. Each event handler can be a simple function or a more complex function that uses a state machine or other control logic.

## Orchestrating Agents

If is possible to build a functional and scalable agent system that only reacts to external events. In many cases, however, you will want to orchestrate the agents to achieve a specific goal or follow a pre-determined workflow. In this case, you will need to build an orchestrator agent that manages the flow of events between agents.

## Built-in Event Types

The Starfleet system comes with a set of built-in event types that are used to manage the system. These include:

* System Events - Events that are used to manage the system itself. These include events for starting and stopping the Agents, sending messages to all agents, and other system-level events.
* ? insert other types here ?

## Agent Contracts

You may want to leverage more prescriptive agent behavior contracts, and Starfleet also includes base agents that implement different approaches to agent behavior, including layering request/response patterns on top of the event-driven model. For an example of this see the ChatAgents in the Python examples. In this case your agent will have a known set of events which it must implement and specific behaviors expected of those events.
