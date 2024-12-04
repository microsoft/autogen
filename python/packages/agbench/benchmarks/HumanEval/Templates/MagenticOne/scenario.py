import asyncio
import logging

from autogen_core import AgentId, AgentProxy, TopicId
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.application.logging import EVENT_LOGGER_NAME
from autogen_core import DefaultSubscription, DefaultTopicId
from autogen_core.components.code_executor import LocalCommandLineCodeExecutor
from autogen_core.components.models import (
    UserMessage,
)

from autogen_magentic_one.agents.coder import Coder, Executor
from autogen_magentic_one.agents.orchestrator import RoundRobinOrchestrator
from autogen_magentic_one.messages import BroadcastMessage, OrchestrationEvent
from autogen_magentic_one.utils import create_completion_client_from_env


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create the AzureOpenAI client
    client = create_completion_client_from_env()

    # Register agents.
    await runtime.register(
        "Coder",
        lambda: Coder(model_client=client),
        subscriptions=lambda: [DefaultSubscription()],
    )
    coder = AgentProxy(AgentId("Coder", "default"), runtime)

    await runtime.register(
        "Executor",
        lambda: Executor(
            "A agent for executing code", executor=LocalCommandLineCodeExecutor(), confirm_execution="ACCEPT_ALL"
        ),
        subscriptions=lambda: [DefaultSubscription()],
    )
    executor = AgentProxy(AgentId("Executor", "default"), runtime)

    await runtime.register(
        "Orchestrator",
        lambda: RoundRobinOrchestrator([coder, executor]),
        subscriptions=lambda: [DefaultSubscription()],
    )

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

    runtime.start()

    await runtime.publish_message(
        BroadcastMessage(content=UserMessage(content=task, source="human")),
        topic_id=DefaultTopicId(),
    )

    await runtime.stop_when_idle()


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
