# Examples

This directory contains examples and demos of how to use AGNext.

## Core examples

We provide examples to illustrate the core concepts of AGNext:
agents, runtime, and message passing APIs.

- [`inner_outer.py`](inner_outer.py): A simple example of how to create custom agent and message type.
- [`mixture_of_agents_direct.py`](mixture_of_agents_direct.py): An example of how to create a [mixture of agents](https://github.com/togethercomputer/moa) that communicate using async direct messaging API.
- [`mixture_of_agents_pub_sub.py`](mixture_of_agents_pub_sub.py): An example of how to create a [mixture of agents](https://github.com/togethercomputer/moa) that communicate using publish-subscribe API.
- [`coder_reviewer_direct.py`](coder_reviewer_direct.py): An example of how to create a coder-reviewer reflection pattern using async direct messaging API.
- [`coder_reviewer_pub_sub.py`](coder_reviewer_pub_sub.py): An example of how to create a coder-reviewer reflection pattern using publish-subscribe API.

## Demos

We provide interactive demos that showcase the capabilities of AGNext:

- `assistant.py`: a demonstration of how to use the OpenAI Assistant API to create
    a ChatGPT agent.
- `chat_room.py`: An example of how to create a chat room of custom agents without
    a centralized orchestrator.
- `illustrator_critics.py`: a demo that uses an illustrator, critics and descriptor agent
    to implement the reflection pattern for image generation.
- `chest_game.py`: a demo that two chess player agents to demonstrate tool use and reflection
    on tool use.
- `software_consultancy.py`: a demonstration of multi-agent interaction using
    the group chat pattern.
- `orchestrator.py`: a demonstration of multi-agent problem solving using
    the orchestrator pattern.

## Running the examples and demos

First, you need a shell with AGNext and the examples dependencies installed. To do this, run:

```bash
hatch shell
```

To run an example, just run the corresponding Python script. For example, to run the `coder_reviewer.py` example, run:

```bash
hatch shell
python coder_reviewer.py
```

Or simply:

```bash
hatch run python coder_reviewer.py
```

To enable logging, turn on verbose mode by setting `--verbose` flag:

```bash
hatch run python coder_reviewer.py --verbose
```

By default the log file is saved in the same directory with the same filename
as the script, e.g., "coder_reviewer.log".
