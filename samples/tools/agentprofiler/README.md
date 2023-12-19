# AutoGen Profiler

AutoGen Profiler is a set of utilities for analyzing and visualizing multi-agent conversations.


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
