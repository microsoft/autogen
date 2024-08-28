# AGNext Architecture

AGNext is a framework for building multi-agent applications with AI agents.
At the foundation level, it provides a runtime envionment to facilitate
communication between agents, manage their identities and lifecycles,
and enforce security and privacy boundaries.

## Runtime Architecture

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
routed agent, AI model clients, tools for AI models, code execution sandboxes,
memory stores, and more.

## API Layers

The API consists of the following layers:

- {py:mod}`agnext.base`
- {py:mod}`agnext.application`
- {py:mod}`agnext.components`

The following diagram shows the relationship between the layers.

![AGNext Layers](agnext-layers.svg)

The {py:mod}`agnext.base` layer defines the
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
