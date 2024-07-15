# Examples

This directory contains examples and demos of how to use AGNext.

- `common`: Contains common implementations and utilities used by the examples.
- `core`: Contains examples that illustrate the core concepts of AGNext.
- `tool-use`: Contains examples that illustrate tool use in AGNext.
- `patterns`: Contains examples that illustrate how multi-agent patterns can be implemented in AGNext.
- `demos`: Contains interactive demos that showcase applications that can be built using AGNext.

See [Running the examples](#running-the-examples) for instructions on how to run the examples.

## Core examples

We provide examples to illustrate the core concepts of AGNext: agents, runtime, and message passing.

- [`one_agent_direct.py`](core/one_agent_direct.py): A simple example of how to create a single agent powered by ChatCompletion model client. Communicate with the agent using direct communication.
- [`inner_outer_direct.py`](core/inner_outer_direct.py): A simple example of how to create an agent that calls an inner agent using direct communication.
- [`two_agents_pub_sub.py`](core/two_agents_pub_sub.py): An example of how to create two agents that communicate using broadcast communication (i.e., pub/sub).

## Tool use examples

We provide examples to illustrate how to use tools in AGNext:

- [`coding_one_agent_direct.py`](tool-use/coding_one_agent_direct.py): a code execution example with one agent that calls and executes tools to demonstrate tool use and reflection on tool use. This example uses direct communication.
- [`coding_two_agent_pub_sub.py`](tool-use/coding_two_agent_pub_sub.py): a code execution example with two agents, one for calling tool and one for executing the tool, to demonstrate tool use and reflection on tool use. This example uses broadcast communication.
- [`custom_function_tool_one_agent_direct.py`](tool-use/custom_function_tool_one_agent_direct.py): a custom function tool example with one agent that calls and executes tools to demonstrate tool use and reflection on tool use. This example uses direct communication.

## Pattern examples

We provide examples to illustrate how multi-agent patterns can be implemented in AGNext:

- [`coder_executor.py`](patterns/coder_executor.py): An example of how to create a coder-executor reflection pattern. This example creates a plot of stock prices using the Yahoo Finance API.
- [`coder_reviewer.py`](patterns/coder_reviewer.py): An example of how to create a coder-reviewer reflection pattern.
- [`group_chat.py`](patterns/group_chat.py): An example of how to create a round-robin group chat among three agents.
- [`mixture_of_agents.py`](patterns/mixture_of_agents.py): An example of how to create a [mixture of agents](https://github.com/togethercomputer/moa).
- [`multi_agent_debate.py`](patterns/multi_agent_debate.py): An example of how to create a [sparse multi-agent debate](https://arxiv.org/abs/2406.11776) pattern.

## Demos

We provide interactive demos that showcase applications that can be built using AGNext:

- [`assistant.py`](demos/assistant.py): a demonstration of how to use the OpenAI Assistant API to create
    a ChatGPT agent.
- [`chat_room.py`](demos/chat_room.py): An example of how to create a chat room of custom agents without
    a centralized orchestrator.
- [`illustrator_critics.py`](demos/illustrator_critics.py): a demo that uses an illustrator, critics and descriptor agent
    to implement the reflection pattern for image generation.
- [`software_consultancy.py`](demos/software_consultancy.py): a demonstration of multi-agent interaction using
    the group chat pattern.
- [`chest_game.py`](demos/chess_game.py): an example with two chess player agents that executes its own tools to demonstrate tool use and reflection on tool use.

## Running the examples

### Prerequisites

First, you need a shell with AGNext and the examples dependencies installed.
To do this, in the example directory, run:

```bash
hatch shell
```

Then, you need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key.

```bash
export OPENAI_API_KEY=your_openai_api_key
```

For Azure OpenAI API, you need to set the following environment variables:

```bash
export AZURE_OPENAI_API_KEY=your_azure_openai_api_key
export AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
```

By default, OpenAI API is used.
To use Azure OpenAI API, set the `OPENAI_API_TYPE`
environment variable to `azure`.

```bash
export OPENAI_API_TYPE=azure
```

### Running

To run an example, just run the corresponding Python script. For example:

```bash
hatch shell
python core/one_agent_direct.py
```

Or simply:

```bash
hatch run python core/one_agent_direct.py
```
