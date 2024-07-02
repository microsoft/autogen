import asyncio
#from typing import Any, Dict, List, Tuple, Union

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import (
    AzureOpenAIChatCompletionClient,
    LLMMessage,
    ModelCapabilities,
    UserMessage,
)
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.messages import BroadcastMessage

async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create the AzureOpenAI client, with AAD auth
    #token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAIChatCompletionClient(
        api_version="2024-02-15-preview",
        azure_endpoint="https://aif-complex-tasks-west-us-3.openai.azure.com/",
        model="gpt-4o-2024-05-13",
        model_capabilities=ModelCapabilities(function_calling=True, json_output=True, vision=True),
        #azure_ad_token_provider=token_provider
    )

    # Register agents.
    coder = runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )
    executor = runtime.register_and_get_proxy(
        "Executor",
        lambda: Executor("A agent for executing code", executor=LocalCommandLineCodeExecutor())
    )

    runtime.register("orchestrator", lambda: RoundRobinOrchestrator([coder, executor]))

    prompt = ""
    with open("prompt.txt", "rt") as fh:
        prompt = fh.read()

    entry_point = "__ENTRY_POINT__" 

    task = f"""
The following python code imports the `run_tests` function from unit_tests.py, and runs
it on the function `{entry_point}`. This will run a set of automated unit tests to verify the
correct implementation of `{entry_point}`. However, `{entry_point}` is only partially
implemented in the code below. Complete the implementation of `{entry_point}` and then execute
a new stand-alone code block that contains everything needed to run the tests, including: importing
`unit_tests`, calling `run_tests({entry_point})`, as well as {entry_point}'s complete definition,
such that this code block can be run directly in Python.

```python
from unit_tests import run_tests

{prompt}

# Run the unit tests
run_tests({entry_point})
```
""".strip()


    await runtime.publish_message(BroadcastMessage(content=UserMessage(content=task, source="human")), namespace="default")

    # Run the runtime until the task is completed.
    await runtime.process_until_idle()

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())

