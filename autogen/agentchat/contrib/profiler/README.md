# AutoGen Agent Profiler

This repository contains utilities that provide visibility into the activities of AI agents. Currently, there are two main utilities: `annotate_chat_history` and `draw_profiler_graph`.

## Utilities

### annotate_chat_history

This utility takes a chat history as input and annotates it using GPT-4. It predicts if a predefined set of codes apply to a given message. The output is an annotated chat history.

### draw_profiler_graph

This utility takes the annotated chat history from `annotate_chat_history` as input and generates a graph. This graph provides a visual representation of the agent's activities over time.

## Interpreting the Chart

To interpret the resulting chart, look for patterns in the agent's activities. For example, if a certain code is frequently applied, it might indicate that the agent often performs a certain action.



## Quick Start

Please add this subpackage to your path

```
export PYTHONPATH="$PYTHONPATH;<path to repo>/samples/tools"
```


```python
import os
import json

from autogen import config_list_from_json
from agentprofiler import annotate_chat_history, draw_profiler_graph

data_dir = os.path.join("..", "sample_data")
chat_history_file = os.path.join(data_dir, "chat_history.json")

# Load chat history
chat_history = json.load(open(chat_history_file))

llm_config = config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={"model": ["gpt-4"]},
    )[0]

# Annotate chat history
annotated_chat_history = annotate_chat_history(chat_history, llm_config=llm_config)

# Visualize annotated chat history
draw_profiler_graph(
    annotated_chat_history,
    title="ArXiv Search w/ GPT-4",
    output_dir=data_dir,
    filename="profiler_graph.png",
)

```
