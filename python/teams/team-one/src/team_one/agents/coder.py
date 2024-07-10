import asyncio
import re
from typing import List, Optional, Tuple, Union

from agnext.components.code_executor import CodeBlock, CodeExecutor, LocalCommandLineCodeExecutor
from agnext.components.models import (
    ChatCompletionClient,
    SystemMessage,
)
from agnext.core import CancellationToken

from ..messages import UserContent
from .base_agent import BaseAgent


class Coder(BaseAgent):
    """An agent that uses tools to write, execute, and debug Python code."""

    DEFAULT_DESCRIPTION = "A Python coder assistant."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage("""You are a helpful AI assistant. Solve tasks using your Python coding skills. The code you output must be formatted in Markdown code blocks demarcated by triple backticks (```). As an example:

```python

def main():
    print("Hello world.")

if __name__ == "__main__":
    main()
```

The user cannot provide any feedback or perform any other action beyond executing the code you suggest. In particular, the user can't modify your code, and can't copy and paste anything, and can't fill in missing values. Thus, do not suggest incomplete code which requires users to perform any of these actions.

The user will run all code that you provide, and will report back the results. When receiving the results, check if the output indicates an error. Fix the error. When fixing the error, output the full code, as before, instead of partial code or code changes -- code blocks must stand alone and be ready to execute without modification. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, and think of a different approach to try.

If the code was executed, and the output appears to indicate that the original prolem was solved successful, reply "TERMINATE". UNDER NO OTHER CONDITIONS SHOULD "TERMINATE" BE USED.
""")
    ]

    def __init__(
        self,
        model_client: ChatCompletionClient,
        description: str = DEFAULT_DESCRIPTION,
        system_messages: List[SystemMessage] = DEFAULT_SYSTEM_MESSAGES,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Respond to a reply request."""

        # Make an inference to the model.
        response = await self._model_client.create(self._system_messages + self._chat_history)
        assert isinstance(response.content, str)
        return "TERMINATE" in response.content, response.content


class Executor(BaseAgent):
    def __init__(self, description: str, executor: Optional[CodeExecutor] = None) -> None:
        super().__init__(description)
        self._executor = executor or LocalCommandLineCodeExecutor()

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        """Respond to a reply request."""

        # Extract code block from the message.
        assert isinstance(self._chat_history[-1].content, str)
        code = self._extract_execution_request(self._chat_history[-1].content)
        if code is not None:
            execution_requests = [CodeBlock(code=code, language="python")]
            future = asyncio.get_event_loop().run_in_executor(
                None, self._executor.execute_code_blocks, execution_requests
            )
            cancellation_token.link_future(future)
            result = await future
            return (
                False,
                f"The script ran, then exited with Unix exit code: {result.exit_code}\nIts output was:\n{result.output}",
            )
        else:
            return (
                False,
                "No code block detected. Please provide a markdown-encoded code block to execute for the original task.",
            )

    def _extract_execution_request(self, markdown_text: str) -> Union[str, None]:
        pattern = r"```(\w+)\n(.*?)\n```"
        # Search for the pattern in the markdown text
        match = re.search(pattern, markdown_text, re.DOTALL)
        # Extract the language and code block if a match is found
        if match:
            return match.group(2)
        return None
