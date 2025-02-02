import re
from typing import List, Sequence

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, CodeExecutor

from ..base import Response
from ..messages import ChatMessage, TextMessage
from ._base_chat_agent import BaseChatAgent


class CodeExecutorAgent(BaseChatAgent):
    """An agent that extracts and executes code snippets found in received messages and returns the output.

    It is typically used within a team with another agent that generates code snippets to be executed.

    Args:
        name: The name of the agent.
        code_executor: The CodeExecutor responsible for executing code received in messages (:py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` recommended. See example below)
        description (optional): The description of the agent.
        sources (optional): Check only messages from the specified agents for the code to execute.


    .. note::

        It is recommended that the `CodeExecutorAgent` agent uses a Docker container to execute code. This ensures that model-generated code is executed in an isolated environment. To use Docker, your environment must have Docker installed and running.
        Follow the installation instructions for `Docker <https://docs.docker.com/get-docker/>`_.

    In this example, we show how to set up a `CodeExecutorAgent` agent that uses the
    :py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`
    to execute code snippets in a Docker container. The `work_dir` parameter indicates where all executed files are first saved locally before being executed in the Docker container.

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import CodeExecutorAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
            from autogen_core import CancellationToken


            async def run_code_executor_agent() -> None:
                # Create a code executor agent that uses a Docker container to execute code.
                code_executor = DockerCommandLineCodeExecutor(work_dir="coding")
                await code_executor.start()
                code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)

                # Run the agent with a given code snippet.
                task = TextMessage(
                    content='''Here is some code
            ```python
            print('Hello world')
            ```
            ''',
                    source="user",
                )
                response = await code_executor_agent.on_messages([task], CancellationToken())
                print(response.chat_message)

                # Stop the code executor.
                await code_executor.stop()


            asyncio.run(run_code_executor_agent())

    """

    def __init__(
        self,
        name: str,
        code_executor: CodeExecutor,
        *,
        description: str = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks).",
        sources: Sequence[str] | None = None,
    ) -> None:
        super().__init__(name=name, description=description)
        self._code_executor = code_executor
        self._sources = sources

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the code executor agent produces."""
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        # Extract code blocks from the messages.
        code_blocks: List[CodeBlock] = []
        for msg in messages:
            if isinstance(msg, TextMessage):
                if self._sources is None or msg.source in self._sources:
                    code_blocks.extend(self._extract_markdown_code_blocks(msg.content))
        if code_blocks:
            # Execute the code blocks.
            result = await self._code_executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

            code_output = result.output
            if code_output.strip() == "":
                # No output
                code_output = f"The script ran but produced no output to console. The POSIX exit code was: {result.exit_code}. If you were expecting output, consider revising the script to ensure content is printed to stdout."
            elif result.exit_code != 0:
                # Error
                code_output = f"The script ran, then exited with an error (POSIX exit code: {result.exit_code})\nIts output was:\n{result.output}"

            return Response(chat_message=TextMessage(content=code_output, source=self.name))
        else:
            return Response(
                chat_message=TextMessage(
                    content="No code blocks found in the thread. Please provide at least one markdown-encoded code block to execute (i.e., quoting code in ```python or ```sh code blocks).",
                    source=self.name,
                )
            )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """It it's a no-op as the code executor agent has no mutable state."""
        pass

    def _extract_markdown_code_blocks(self, markdown_text: str) -> List[CodeBlock]:
        pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
        matches = pattern.findall(markdown_text)
        code_blocks: List[CodeBlock] = []
        for match in matches:
            language = match[0].strip() if match[0] else ""
            code_content = match[1]
            code_blocks.append(CodeBlock(code=code_content, language=language))
        return code_blocks
