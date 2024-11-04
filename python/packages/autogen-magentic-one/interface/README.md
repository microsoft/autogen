# MagenticOne Interface

This repository contains a previewe interface for interacting with the MagenticOne system. It includes helper classes, a log viewer, and example usage.



## Installation

Make sure to clone AutoGen first:

```sh
git clone https://github.com/microsoft/autogen.git
cd autogen/python/packages/autogen-magentic-one/interface
```

You need to have installed autogen-magentic-one and set it up based on [magentic-one README](../README.md).

To run the log viewer you need to install these additional dependencies, run:

```sh
pip install flask markdown
```


## Usage

### MagenticOneHelper

The MagenticOneHelper class provides an interface to interact with the MagenticOne system. It saves logs to a user-specified directory and provides methods to run tasks, stream logs, and retrieve the final answer.

The class provides the following methods:
- async initialize(self) -> None: Initializes the MagenticOne system, setting up agents and runtime.
- async run_task(self, task: str) -> None: Runs a specific task through the MagenticOne system.
- get_final_answer(self) -> Optional[str]: Retrieves the final answer from the Orchestrator.
- async stream_logs(self) -> AsyncGenerator[Dict[str, Any], None]: Streams logs from the system as they are generated.
- get_all_logs(self) -> List[Dict[str, Any]]: Retrieves all logs that have been collected so far.

We show an example of how to use the MagenticOneHelper class to in [example_magentic_one_helper.py](example_magentic_one_helper.py).

```python
from magentic_one_helper import MagenticOneHelper
import asyncio
import json

async def magentic_one_example():
    # Create and initialize MagenticOne
    magnetic_one = MagenticOneHelper(logs_dir="./logs")
    await magnetic_one.initialize()
    print("MagenticOne initialized.")
    
    # Start a task and stream logs
    task = "How many members are in the MSR HAX Team"
    task_future = asyncio.create_task(magnetic_one.run_task(task))

    # Stream and process logs
    async for log_entry in magnetic_one.stream_logs():
        print(json.dumps(log_entry, indent=2))

    # Wait for task to complete
    await task_future

    # Get the final answer
    final_answer = magnetic_one.get_final_answer()

    if final_answer is not None:
        print(f"Final answer: {final_answer}")
    else:
        print("No final answer found in logs.")
```

### Log Viewer

The log viewer python file is commented out, you need to uncomment the entire file to run it. It is not secure to run, so run at your own risk.

You need to generate logs by having MagenticOne save screenshots and logs. You can do this by running the example code with the `--save_screenshots` flag or by setting the `save_screenshots` attribute to `True` in the `MagenticOneHelper` class.

To run the log viewer, use the following command:

```sh
python log_viewer.py <log_folder> --port <port>
```

Where:
- <log_folder>: Path to the folder containing JSONL log files.
- <port>: Port number to run the server on (default: 5000).

The log viewer provides a web interface to view logs in the browser. It will start by default on http://localhost:5000.
