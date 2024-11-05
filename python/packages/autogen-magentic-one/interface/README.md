# MagenticOne Interface

This repository contains a preview interface for interacting with the MagenticOne system. It includes helper classes, and example usage.


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
