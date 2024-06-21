# Examples

This directory contains examples of how to use AGNext.

## `chat` layer examples

We provide examples that use pre-built agents and message types in the `chat` layer.
These examples are intended for users who want to quickly create
demos and experimenting with multi-agent design paterns.

### Single agent examples

- `assistant.py`: a demonstration of how to use the OpenAI Assistant API to create
    a ChatGPT agent.

### Reflection pattern examples

- `coder_reviewer.py`: using a coder and reviewer agents to implement the
    reflection pattern for code generation.
- `illustrator_critics.py`: using an illustrator, critics and descriptor agent
    to implement the reflection pattern for image generation.
- `chest_game.py`: using two chess player agents to demonstrate tool use and reflection
    on tool use.

### Group chat pattern examples

- `software_consultancy.py`: a demonstration of multi-agent interaction using
    the group chat pattern.

### Orchestrator pattern examples

- `orchestrator.py`: a demonstration of multi-agent problem solving using
    the orchestrator pattern.

## Advanced examples

We also provide examples that use only the `core`, `application`, and `components` layers.
These examples are intended for advanced users who want to create
custom agents and message types for building applications.

- `inner_outer.py`: An example of how to create an inner and outer custom agent.
- `chat_room.py`: An example of how to create a chat room of custom agents without
    a centralized orchestrator.

## Running the examples

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
