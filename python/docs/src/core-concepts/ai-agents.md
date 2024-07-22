# AI Agents

AGNext provides a suite of components to help developers build AI agents.
This section is still under construction.
The best place to start is the [samples](https://github.com/microsoft/agnext/tree/main/python/samples).

## Type-Routed Agent

The {py:class}`~agnext.components.TypeRoutedAgent` base class provides
developer with a simple decorator {py:meth}`~agnext.components.message_handler`
for associating message types with message handlers.

## Model Clients

AGNext provides the {py:mod}`agnext.components.models` module with a suite of built-in
model clients for using ChatCompletion API.

## Tools

Tools can be used together with agents powered by the OpenAI's ChatCompletion or the Assistant API.
AGNext provides the {py:mod}`agnext.components.tools` module with a suite of built-in
tools and utilities for creating and running custom tools.

See [samples](https://github.com/microsoft/agnext/tree/main/python/samples#tool-use-examples)
for how to use the built-in code execution tool and creating custom tools.

## Memory

Memory is a collection of data corresponding to the conversation history
of an agent.
Data in meory can be just a simple list of all messages,
or one which provides a view of the last N messages.

To create a custom memory implementation, you need to subclass the
{py:class}`agnext.components.memory.ChatMemory` protocol class and implement
all its methods.
For example, you can use [LLMLingua](https://github.com/microsoft/LLMLingua)
to create a custom memory implementation that provides a compressed
view of the conversation history.
