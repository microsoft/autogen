import asyncio
import logging

# from typing import Any, Dict, List, Tuple, Union

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import (
    AzureOpenAIChatCompletionClient,
    ModelCapabilities,
    UserMessage,
)
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.application.logging import EVENT_LOGGER_NAME

from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import RoundRobinOrchestrator
from team_one.messages import BroadcastMessage, OrchestrationEvent


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create the AzureOpenAI client, with AAD auth
    # token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAIChatCompletionClient(
        api_version="2024-02-15-preview",
        azure_endpoint="https://aif-complex-tasks-west-us-3.openai.azure.com/",
        model="gpt-4o-2024-05-13",
        model_capabilities=ModelCapabilities(
            function_calling=True, json_output=True, vision=True
        ),
        # azure_ad_token_provider=token_provider
    )

    # Register agents.
    coder = await runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )
    executor = await runtime.register_and_get_proxy(
        "Executor",
        lambda: Executor(
            "A agent for executing code", executor=LocalCommandLineCodeExecutor()
        ),
    )

    await runtime.register("orchestrator", lambda: RoundRobinOrchestrator([coder, executor]))

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

    run_context = runtime.start()

    await runtime.publish_message(
        BroadcastMessage(content=UserMessage(content=task, source="human")),
        namespace="default",
    )

    await run_context.stop_when_idle()


class MyHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, OrchestrationEvent):
                print(f"""---------------------------------------------------------------------------
\033[91m{record.msg.source}:\033[0m

{record.msg.message}""", flush=True)
        except Exception:
            self.handleError(record)


if __name__ == "__main__":

    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    my_handler = MyHandler()
    logger.handlers = [my_handler]
    asyncio.run(main())
