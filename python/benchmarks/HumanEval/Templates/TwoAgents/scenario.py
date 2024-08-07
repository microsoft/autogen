import asyncio
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Union

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.code_executor import (
    CodeBlock,
    CodeExecutor,
    LocalCommandLineCodeExecutor,
)
from agnext.components.models import (
    AssistantMessage,
    AzureOpenAIChatCompletionClient,
    ChatCompletionClient,
    LLMMessage,
    ModelCapabilities,
    SystemMessage,
    UserMessage,
)
from agnext.core import CancellationToken

# from azure.identity import DefaultAzureCredential, get_bearer_token_provider


@dataclass
class TaskMessage:
    content: str


@dataclass
class CodeExecutionRequestMessage:
    session_id: str
    execution_request: str


@dataclass
class CodeExecutionResultMessage:
    session_id: str
    output: str
    exit_code: int


class Coder(TypeRoutedAgent):
    """An agent that uses tools to write, execute, and debug Python code."""

    DEFAULT_DESCRIPTION = "A Python coder assistant."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage(
            """You are a helpful AI assistant. Solve tasks using your Python coding skills. The code you output must be formatted in Markdown code blocks demarcated by triple backticks (```). As an example:

```python

def main():
    print("Hello world.")

if __name__ == "__main__":
    main()
```

The user cannot provide any feedback or perform any other action beyond executing the code you suggest. In particular, the user can't modify your code, and can't copy and paste anything, and can't fill in missing values. Thus, do not suggest incomplete code which requires users to perform any of these actions.

Check the execution result returned by the user. If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes -- code blocks must stand alone and be ready to execute without modification. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, and think of a different approach to try.

If the code has executed successfully, and the problem is stolved, reply "TERMINATE".
"""
        )
    ]

    def __init__(
        self,
        model_client: ChatCompletionClient,
        description: str = DEFAULT_DESCRIPTION,
        system_messages: List[SystemMessage] = DEFAULT_SYSTEM_MESSAGES,
        max_turns: int | None = None,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._session_memory: Dict[str, List[LLMMessage]] = {}
        self._max_turns = max_turns

    @message_handler
    async def handle_user_message(
        self, message: TaskMessage, cancellation_token: CancellationToken
    ) -> None:
        """Handle a user message, execute the model and tools, and returns the response."""
        # Create a new session.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(
            UserMessage(content=message.content, source="user")
        )

        # Make an inference to the model.
        response = await self._model_client.create(
            self._system_messages + self._session_memory[session_id]
        )
        assert isinstance(response.content, str)
        self._session_memory[session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )

        await self.publish_message(
            CodeExecutionRequestMessage(
                execution_request=response.content, session_id=session_id
            ),
            cancellation_token=cancellation_token,
        )

    @message_handler
    async def handle_code_execution_result(
        self, message: CodeExecutionResultMessage, cancellation_token: CancellationToken
    ) -> None:

        execution_result = f"The script ran, then exited with Unix exit code: {message.exit_code}\nIts output was:\n{message.output}"

        # Store the code execution output.
        self._session_memory[message.session_id].append(
            UserMessage(content=execution_result, source="user")
        )

        # Count the number of rounds so far
        if self._max_turns is not None:
            n_turns = sum(
                1
                for message in self._session_memory[message.session_id]
                if isinstance(message, AssistantMessage)
            )
            if n_turns >= self._max_turns:
                return

        # Make an inference to the model.
        response = await self._model_client.create(
            self._system_messages + self._session_memory[message.session_id]
        )
        assert isinstance(response.content, str)
        self._session_memory[message.session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )

        if "TERMINATE" in response.content:
            return
        else:
            await self.publish_message(
                CodeExecutionRequestMessage(
                    execution_request=response.content, session_id=message.session_id
                ),
                cancellation_token=cancellation_token,
            )


class Executor(TypeRoutedAgent):

    def __init__(self, description: str, executor: CodeExecutor) -> None:
        super().__init__(description)
        self._executor = executor

    @message_handler
    async def handle_code_execution(
        self,
        message: CodeExecutionRequestMessage,
        cancellation_token: CancellationToken,
    ) -> None:

        # Extract code block from the message.
        code = self._extract_execution_request(message.execution_request)
        if code is not None:
            execution_requests = [CodeBlock(code=code, language="python")]
            result = await self._executor.execute_code_blocks(execution_requests, cancellation_token)
            await self.publish_message(
                CodeExecutionResultMessage(
                    output=result.output,
                    exit_code=result.exit_code,
                    session_id=message.session_id,
                )
            )
        else:
            await self.publish_message(
                CodeExecutionResultMessage(
                    output="No code block detected. Please provide a markdown-encoded code block to execute.",
                    exit_code=1,
                    session_id=message.session_id,
                )
            )

    def _extract_execution_request(self, markdown_text: str) -> Union[str, None]:
        pattern = r"```(\w+)\n(.*?)\n```"
        # Search for the pattern in the markdown text
        match = re.search(pattern, markdown_text, re.DOTALL)
        # Extract the language and code block if a match is found
        if match:
            return match.group(2)
        return None


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
    coder = await runtime.register_and_get(
        "Coder",
        lambda: Coder(model_client=client),
    )
    await runtime.register(
        "Executor",
        lambda: Executor(
            "A agent for executing code", executor=LocalCommandLineCodeExecutor()
        ),
    )

    prompt = ""
    with open("prompt.txt", "rt") as fh:
        prompt = fh.read()

    entry_point = "__ENTRY_POINT__"

    task = TaskMessage(
        f"""
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
    )

    # Run the runtime until the task is completed.
    run_context = runtime.start()
    # Send a task to the tool user.
    await runtime.send_message(task, coder)
    await run_context.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
