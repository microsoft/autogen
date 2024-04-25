# `aprofile`

This package introduces a new functionality to profile chat messages. It includes a `Profiler` class that identifies the state of a chat message based on predefined states.
It also introduces a command called `aprofile` which can be used to profile chat messages loaded from files, json str input, and AutoGen Bench style console logs.


## Installation

To install the package, clone the repository and install the dependencies.

```bash
# clone the correct repo/branch
# git clone git@github.com:microsoft/autogen.git
# git checkout ct_webarena
cd samples/tools/profiler
pip install -e .
```

## Demo: API

A demonstration of how to use the `Profiler` class to profile a list of chat messages is provided in `demo.py`.

## Demo: Command-Line Interface
The `aprofile` CLI can accept various input formats.

```bash
# for printing help
aprofile --help
# input: json string
aprofile --json [{"source": "user", "content": "plot a chart"}]
# input: path to a json
aprofile --file chat_history.json
# input: AGBench console log
aprofile --agbconsole <path to AGBench output>/console_log.txt
```
The command utility will print sources observed in the chat and their high-level states.
