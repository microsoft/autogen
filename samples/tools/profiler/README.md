# `aprofile`

`aprofile` is a command-line tool to profile chat messages loaded from files, json str input, and AutoGen Bench style console logs.


## Installation

To install the package, clone the repository and install the dependencies.

```bash
# clone the correct repo/branch
cd samples/tools/profiler
pip install -e .
```

```bash
export OPENAI_API_KEY=<your key>
```

## Usage

The tool currently provides two main commands: `profile` and `visualize`.
For example, to profile a chat log from AutoGenBench style console logs, run:

```bash
aprofile profile --agbconsole <path-to-file> --o profile.json
```

You can then visualize the profile using the `visualize` command:

```bash
aprofile visualize --json profile.json --port 8000
```

This will launch a simple Python HTTP server on port 8000. You can visit the website `localhost:8000` in your browser to interactively visualize the data.
