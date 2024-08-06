# Overview

This section provides the background and overview of AGNext.

## Agent and Multi-Agent Application

An agent is a software entity that
communicates via messages, maintains a state,
and performs actions in response to messages or a change in its state.
Actions can result in changes to the agent's state and external effects,
for example, updating message history, sending a message, executing code,
or making external API calls.

A wide variety of software applications can be modeled as a collection of independent
agents that communicate with each other:
sensors on a factory floor,
distributed services powering web applications,
business workflows involving multiple stakeholders,
and more recently, artificial intelligence (AI) agents powered by language models
(e.g., GPT-4) that can write code and interact with
other software systems.
We refer to them as multi-agent applications.

```{note}
AI agents make use of language models as part of
their software stacks to perform actions. 
```

In a multi-agent application, agents can live in the same process, on the same machine,
or on different machines and across organizational boundaries.
They can be implemented using different AI models, instructions, and programming languages.
They can collaborate and work toward a common goal.

Each agent is a self-contained unit:
developers can build, test and deploy it independently, and reuse it for different scenarios.
Agents are composable: simple agents can form complex applications.

## AGNext Architecture

AGNext is a framework for building multi-agent applications with AI agents.
At the foundation level, it provides a runtime envionment to facilitate
communication between agents, manage their identities and lifecycles,
and enforce security and privacy boundaries.

### Runtime Architecture

The following diagram shows the runtime architecture of AGNext.

![AGNext Runtime](agnext-architecture.svg)

Agent communicate via messages through the runtime.
A runtime, as shown in the diagram,
can consist of a hosted runtime and multiple worker runtimes.
Agents in worker runtimes communicate with other agents via the hosted runtime
through gateways, while agents in the hosted runtime communicate
directly with each other.
Most single-process applications need only an embedded hosted runtime.

AGNext also offers a set of unopinionated and extensible components for building AI agents.
It does not prescribe an abstraction for AI agents, rather, it provides
a minimal base layer that can be extended to suit the application's needs.
Developers can build agents quickly by using the provided components including
type-routed agent, AI model clients, tools for AI models, code execution sandboxes,
memory stores, and more.
Developers can also make use of the provided multi-agent patterns to build
orchestrated workflows, group chat systems, and more.

### API Layers

The API consists of the following layers:

- {py:mod}`agnext.core`
- {py:mod}`agnext.application`
- {py:mod}`agnext.components`

The following diagram shows the relationship between the layers.

![AGNext Layers](agnext-layers.svg)

The {py:mod}`agnext.core` layer defines the
core interfaces and base classes for agents, messages, and runtime.
This layer is the foundation of the framework and is used by the other layers.

The {py:mod}`agnext.application` layer provides concrete implementations of
runtime and utilities like logging for building multi-agent applications.

The {py:mod}`agnext.components` layer provides reusable components for building
AI agents, including type-routed agents, AI model clients, tools for AI models,
code execution sandboxes, and memory stores.

The layers are loosely coupled and can be used independently. For example,
you can swap out the runtime in the {py:mod}`agnext.application` layer with your own
runtime implementation.
You can also skip the components in the {py:mod}`agnext.components` layer and
build your own components.

## AGNext Application Stack

AGNext is designed to be an unopinionated framework that can be used to build
a wide variety of multi-agent applications. It is not tied to any specific
agent abstraction or multi-agent pattern.

The following diagram shows the AGNext application stack.

![AGNext Application Stack](agnext-application-stack.svg)

At the bottom of the stack is the base messaging and routing facilities that
enable agents to communicate with each other. These are managed by the
agent runtime, and for most applications, developers only need to interact
with the high-level APIs provided by the runtime (see [Agent and Agent Runtime](../getting-started/agent-and-agent-runtime.ipynb)).

On top of the communication stack, developers need to define the
types of the messages that agents exchange. A set of message types
forms a behavior contract that agents must adhere to, and the
implementation of the contracts determines how agents handle messages.
The behavior contract is sometimes referred to as the message protocol.
It is the developer's responsibility to implement the behavior contract.
Multi-agent patterns are design patterns that emerge from behavior contracts
(see [Multi-Agent Design Patterns](../getting-started/multi-agent-design-patterns.ipynb)).

### An Example Application

Consider a concrete example of a multi-agent application for
code generation. The application consists of three agents:
Coder Agent, Executor Agent, and Reviewer Agent.
The following diagram shows the data flow between the agents,
and the message types exchanged between them.

![Code Generation Example](agnext-code-gen-example.svg)

In this example, the behavior contract consists of the following:

- `CodingTaskMsg` message from application to the Coder Agent
- `CodeGenMsg` from Coder Agent to Executor Agent
- `ExecutionResultMsg` from Executor Agent to Reviewer Agent
- `ReviewMsg` from Reviewer Agent to Coder Agent
- `CodingResultMsg` from the Reviewer Agent to the application

The behavior contract is implemented by the agents' handling of these messages. For example, the Reviewer Agent listens for `ExecutionResultMsg`
and evaluates the code execution result to decide whether to approve or reject,
if approved, it sends a `CodingResultMsg` to the application,
otherwise, it sends a `ReviewMsg` to the Coder Agent for another round of
code generation.

This behavior contract is a case of a multi-agent pattern called Reflection,
where a generation result is reviewed by another round of generation,
to improve the overall quality.
