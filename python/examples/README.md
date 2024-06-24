# Examples

This directory contains examples and demos of how to use AGNext.

## Core examples

We provide examples to illustrate the core concepts of AGNext:
agents, runtime, and message passing APIs.

- [`one_agent_direct.py`](core/one_agent_direct.py): A simple example of how to create a single agent powered by ChatCompletion model client. Communicate with the agent using async direct messaging API.
- [`inner_outer_direct.py`](core/inner_outer_direct.py): A simple example of how to create an agent that calls an inner agent using async direct messaging API.
- [`two_agents_pub_sub.py`](core/two_agents_pub_sub.py): An example of how to create two agents that communicate using publish-subscribe API.
- [`mixture_of_agents_direct.py`](core/mixture_of_agents_direct.py): An example of how to create a [mixture of agents](https://github.com/togethercomputer/moa) that communicate using async direct messaging API.
- [`mixture_of_agents_pub_sub.py`](core/mixture_of_agents_pub_sub.py): An example of how to create a [mixture of agents](https://github.com/togethercomputer/moa) that communicate using publish-subscribe API.
- [`coder_reviewer_direct.py`](core/coder_reviewer_direct.py): An example of how to create a coder-reviewer reflection pattern using async direct messaging API.
- [`coder_reviewer_pub_sub.py`](core/coder_reviewer_pub_sub.py): An example of how to create a coder-reviewer reflection pattern using publish-subscribe API.

## Tool use examples

We provide examples to illustrate how to use tools in AGNext:

- [`coding_one_agent_direct.py`](tool-use/coding_two_agent_direct.py): a code execution example with one agent that calls and executes tools to demonstrate tool use and reflection on tool use. This example uses the async direct messaging API.
- [`coding_two_agent_direct.py`](tool-use/coding_two_agent_direct.py): a code execution example with two agents, one for calling tool and one for executing the tool, to demonstrate tool use and reflection on tool use. This example uses the async direct messaging API.
- [`coding_two_agent_pub_sub.py`](tool-use/coding_two_agent_pub_sub.py): a code execution example with two agents, one for calling tool and one for executing the tool, to demonstrate tool use and reflection on tool use. This example uses the publish-subscribe API.
- [`custom_function_tool_one_agent_direct.py`](tool-use/custom_function_tool_one_agent_direct.py): a custom function tool example with one agent that calls and executes tools to demonstrate tool use and reflection on tool use. This example uses the async direct messaging API.

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
- [`chest_game.py`](tool-use/chess_game.py): an example with two chess player agents that executes its own tools to demonstrate tool use and reflection on tool use.

## Running the examples and demos

First, you need a shell with AGNext and the examples dependencies installed. To do this, run:

```bash
hatch shell
```

To run an example, just run the corresponding Python script. For example, to run the `coder_reviewer_pub_sub.py` example, run:

```bash
hatch shell
python core/coder_reviewer.py
```

Or simply:

```bash
hatch run python core/coder_reviewer.py
```

To enable logging, turn on verbose mode by setting `--verbose` flag:

```bash
hatch run python core/coder_reviewer.py --verbose
```

By default the log file is saved in the same directory with the same filename
as the script, e.g., "coder_reviewer.log".
