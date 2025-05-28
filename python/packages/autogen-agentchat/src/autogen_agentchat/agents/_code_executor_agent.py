import logging
import re
from typing import (
    AsyncGenerator,
    List,
    Optional,
    Sequence,
    Union,
)

from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.code_executor import CodeBlock, CodeExecutor, CodeResult
from autogen_core.model_context import (
    ChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel
from typing_extensions import Self

from .. import EVENT_LOGGER_NAME
from ..base import Response
from ..messages import (
    BaseAgentEvent,
    BaseChatMessage,
    CodeExecutionEvent,
    CodeGenerationEvent,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ThoughtEvent,
)
from ..utils import remove_images
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class CodeExecutorAgentConfig(BaseModel):
    """Configuration for CodeExecutorAgent"""

    name: str
    code_executor: ComponentModel
    model_client: ComponentModel | None = None
    description: str | None = None
    sources: List[str] | None = None
    system_message: str | None = None
    model_client_stream: bool = False
    model_context: ComponentModel | None = None
    supported_languages: List[str] | None = None


class RetryDecision(BaseModel):
    reason: str
    retry: bool


class CodeExecutorAgent(BaseChatAgent, Component[CodeExecutorAgentConfig]):
    """(Experimental) An agent that generates and executes code snippets based on user instructions.

    .. note::

        This agent is experimental and may change in future releases.

    It is typically used within a team with another agent that generates code snippets
    to be executed or alone with `model_client` provided so that it can generate code
    based on user query, execute it and reflect on the code result.

    When used with `model_client`, it will generate code snippets using the model
    and execute them using the provided `code_executor`. The model will also reflect on the
    code execution results. The agent will yield the final reflection result from the model
    as the final response.

    When used without `model_client`, it will only execute code blocks found in
    :class:`~autogen_agentchat.messages.TextMessage` messages and returns the output
    of the code execution.

    .. note::

        Using :class:`~autogen_agentchat.agents.AssistantAgent` with
        :class:`~autogen_ext.tools.code_execution.PythonCodeExecutionTool`
        is an alternative to this agent. However, the model for that agent will
        have to generate properly escaped code string as a parameter to the tool.

    Args:
        name (str): The name of the agent.
        code_executor (CodeExecutor): The code executor responsible for executing code received in messages
            (:py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` recommended. See example below)
        model_client (ChatCompletionClient, optional): The model client to use for inference and generating code.
            If not provided, the agent will only execute code blocks found in input messages.
            Currently, the model must support structured output mode, which is required for
            the automatic retry mechanism to work.
        model_client_stream (bool, optional): If `True`, the model client will be used in streaming mode.
            :meth:`on_messages_stream` and :meth:`BaseChatAgent.run_stream` methods will
            also yield :class:`~autogen_agentchat.messages.ModelClientStreamingChunkEvent`
            messages as the model client produces chunks of response. Defaults to `False`.
        description (str, optional): The description of the agent. If not provided,
            :class:`~autogen_agentchat.agents.CodeExecutorAgent.DEFAULT_AGENT_DESCRIPTION` will be used.
        system_message (str, optional): The system message for the model. If provided, it will be prepended to the messages in the model context when making an inference. Set to `None` to disable.
            Defaults to :class:`~autogen_agentchat.agents.CodeExecutorAgent.DEFAULT_SYSTEM_MESSAGE`. This is only used if `model_client` is provided.
        sources (Sequence[str], optional): Check only messages from the specified agents for the code to execute.
            This is useful when the agent is part of a group chat and you want to limit the code execution to messages from specific agents.
            If not provided, all messages will be checked for code blocks.
            This is only used if `model_client` is not provided.
        max_retries_on_error (int, optional): The maximum number of retries on error. If the code execution fails, the agent will retry up to this number of times.
            If the code execution fails after this number of retries, the agent will yield a reflection result.
        supported_languages (List[str], optional): List of programming languages that will be parsed and executed from agent response;
            others will be ignored. Defaults to ["python", "bash"].


    .. note::

        It is recommended that the `CodeExecutorAgent` agent uses a Docker container to execute code. This ensures that model-generated code is executed in an isolated environment. To use Docker, your environment must have Docker installed and running.
        Follow the installation instructions for `Docker <https://docs.docker.com/get-docker/>`_.

    .. note::

        The code executor only processes code that is properly formatted in markdown code blocks using triple backticks.
        For example:

        .. code-block:: text

            ```python
            print("Hello World")
            ```

            # or

            ```sh
            echo "Hello World"
            ```

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

    In this example, we show how to set up a `CodeExecutorAgent` agent that uses the
    :py:class:`~docker.types.DeviceRequest` to expose a GPU to the container for cuda-accelerated code execution.

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import CodeExecutorAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
            from autogen_core import CancellationToken
            from docker.types import DeviceRequest


            async def run_code_executor_agent() -> None:
                # Create a code executor agent that uses a Docker container to execute code.
                code_executor = DockerCommandLineCodeExecutor(
                    work_dir="coding", device_requests=[DeviceRequest(count=-1, capabilities=[["gpu"]])]
                )
                await code_executor.start()
                code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)

                # Display the GPU information
                task = TextMessage(
                    content='''Here is some code
            ```bash
            nvidia-smi
            ```
            ''',
                    source="user",
                )
                response = await code_executor_agent.on_messages([task], CancellationToken())
                print(response.chat_message)

                # Stop the code executor.
                await code_executor.stop()


            asyncio.run(run_code_executor_agent())

    In the following example, we show how to setup `CodeExecutorAgent` without `model_client` parameter for executing code blocks generated by other agents in a group chat using :py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`

        .. code-block:: python

            import asyncio

            from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.ui import Console

            termination_condition = MaxMessageTermination(3)


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # define the Docker CLI Code Executor
                code_executor = DockerCommandLineCodeExecutor(work_dir="coding")

                # start the execution container
                await code_executor.start()

                code_executor_agent = CodeExecutorAgent("code_executor_agent", code_executor=code_executor)
                coder_agent = AssistantAgent("coder_agent", model_client=model_client)

                groupchat = RoundRobinGroupChat(
                    participants=[coder_agent, code_executor_agent], termination_condition=termination_condition
                )

                task = "Write python code to print Hello World!"
                await Console(groupchat.run_stream(task=task))

                # stop the execution container
                await code_executor.stop()


            asyncio.run(main())

        .. code-block:: text

            ---------- user ----------
            Write python code to print Hello World!
            ---------- coder_agent ----------
            Certainly! Here's a simple Python code to print "Hello World!":

            ```python
            print("Hello World!")
            ```

            You can run this code in any Python environment to display the message.
            ---------- code_executor_agent ----------
            Hello World!

    In the following example, we show how to setup `CodeExecutorAgent` with `model_client` that can generate its own code without the help of any other agent and executing it in :py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`

        .. code-block:: python

            import asyncio

            from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            from autogen_agentchat.agents import CodeExecutorAgent
            from autogen_agentchat.conditions import TextMessageTermination
            from autogen_agentchat.ui import Console

            termination_condition = TextMessageTermination("code_executor_agent")


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # define the Docker CLI Code Executor
                code_executor = DockerCommandLineCodeExecutor(work_dir="coding")

                # start the execution container
                await code_executor.start()

                code_executor_agent = CodeExecutorAgent(
                    "code_executor_agent", code_executor=code_executor, model_client=model_client
                )

                task = "Write python code to print Hello World!"
                await Console(code_executor_agent.run_stream(task=task))

                # stop the execution container
                await code_executor.stop()


            asyncio.run(main())

        .. code-block:: text

            ---------- user ----------
            Write python code to print Hello World!
            ---------- code_executor_agent ----------
            Certainly! Here is a simple Python code to print "Hello World!" to the console:

            ```python
            print("Hello World!")
            ```

            Let's execute it to confirm the output.
            ---------- code_executor_agent ----------
            Hello World!

            ---------- code_executor_agent ----------
            The code has been executed successfully, and it printed "Hello World!" as expected. If you have any more requests or questions, feel free to ask!

    """

    DEFAULT_TERMINAL_DESCRIPTION = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)."
    DEFAULT_AGENT_DESCRIPTION = "A Code Execution Agent that generates and executes Python and shell scripts based on user instructions. It ensures correctness, efficiency, and minimal errors while gracefully handling edge cases."
    DEFAULT_SYSTEM_MESSAGE = "You are a Code Execution Agent. Your role is to generate and execute Python code and shell scripts based on user instructions, ensuring correctness, efficiency, and minimal errors. Handle edge cases gracefully. Python code should be provided in ```python code blocks, and sh shell scripts should be provided in ```sh code blocks for execution."
    NO_CODE_BLOCKS_FOUND_MESSAGE = "No code blocks found in the thread. Please provide at least one markdown-encoded code block to execute (i.e., quoting code in ```python or ```sh code blocks)."

    component_config_schema = CodeExecutorAgentConfig
    component_provider_override = "autogen_agentchat.agents.CodeExecutorAgent"

    def __init__(
        self,
        name: str,
        code_executor: CodeExecutor,
        *,
        model_client: ChatCompletionClient | None = None,
        model_context: ChatCompletionContext | None = None,
        model_client_stream: bool = False,
        max_retries_on_error: int = 0,
        description: str | None = None,
        system_message: str | None = DEFAULT_SYSTEM_MESSAGE,
        sources: Sequence[str] | None = None,
        supported_languages: List[str] | None = None,
    ) -> None:
        if description is None:
            if model_client is None:
                description = CodeExecutorAgent.DEFAULT_TERMINAL_DESCRIPTION
            else:
                description = CodeExecutorAgent.DEFAULT_AGENT_DESCRIPTION

        super().__init__(name=name, description=description)
        self._code_executor = code_executor
        self._sources = sources
        self._model_client_stream = model_client_stream
        self._max_retries_on_error = max_retries_on_error

        if supported_languages is not None:
            self._supported_languages = supported_languages
        else:
            self._supported_languages = ["python", "bash"]

        self._supported_languages_regex = "|".join(re.escape(lang) for lang in self._supported_languages)

        self._model_client = None
        if model_client is not None:
            self._model_client = model_client

        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()

        self._system_messaages: List[SystemMessage] = []
        if system_message is None:
            self._system_messages = []
        else:
            self._system_messages = [SystemMessage(content=system_message)]

        if self._max_retries_on_error > 0:
            if not self._model_client or not self._model_client.model_info:
                raise ValueError("model_client.model_info must be provided when max_retries_on_error > 0")
            if not self._model_client.model_info["structured_output"]:
                raise ValueError("Specified model_client doesn't support structured output mode.")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        """The types of messages that the code executor agent produces."""
        return (TextMessage,)

    @property
    def model_context(self) -> ChatCompletionContext:
        """
        The model context in use by the agent.
        """
        return self._model_context

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | Response, None]:
        """
        Process the incoming messages with the assistant agent and yield events/responses as they happen.
        """

        # Gather all relevant state here
        agent_name = self.name
        model_context = self._model_context
        system_messages = self._system_messages
        model_client = self._model_client
        model_client_stream = self._model_client_stream
        max_retries_on_error = self._max_retries_on_error

        execution_result: CodeResult | None = None
        if model_client is None:  # default behaviour for backward compatibility
            # execute generated code if present
            code_blocks: List[CodeBlock] = await self.extract_code_blocks_from_messages(messages)
            if not code_blocks:
                yield Response(
                    chat_message=TextMessage(
                        content=self.NO_CODE_BLOCKS_FOUND_MESSAGE,
                        source=agent_name,
                    )
                )
                return
            execution_result = await self.execute_code_block(code_blocks, cancellation_token)
            yield Response(chat_message=TextMessage(content=execution_result.output, source=self.name))
            return

        inner_messages: List[BaseAgentEvent | BaseChatMessage] = []

        for nth_try in range(max_retries_on_error + 1):  # Do one default generation, execution and inference loop
            # Step 1: Add new user/handoff messages to the model context
            await self._add_messages_to_context(
                model_context=model_context,
                messages=messages,
            )

            # Step 2: Run inference with the model context
            model_result = None
            async for inference_output in self._call_llm(
                model_client=model_client,
                model_client_stream=model_client_stream,
                system_messages=system_messages,
                model_context=model_context,
                agent_name=agent_name,
                cancellation_token=cancellation_token,
            ):
                if isinstance(inference_output, CreateResult):
                    model_result = inference_output
                else:
                    # Streaming chunk event
                    yield inference_output

            assert model_result is not None, "No model result was produced."

            # Step 3: [NEW] If the model produced a hidden "thought," yield it as an event
            if model_result.thought:
                thought_event = ThoughtEvent(content=model_result.thought, source=agent_name)
                yield thought_event
                inner_messages.append(thought_event)

            # Step 4: Add the assistant message to the model context (including thought if present)
            await model_context.add_message(
                AssistantMessage(
                    content=model_result.content,
                    source=agent_name,
                    thought=getattr(model_result, "thought", None),
                )
            )

            # Step 5: Extract the code blocks from inferred text
            assert isinstance(model_result.content, str), "Expected inferred model_result.content to be of type str."
            code_blocks = self._extract_markdown_code_blocks(str(model_result.content))

            # Step 6: Exit the loop if no code blocks found
            if not code_blocks:
                yield Response(
                    chat_message=TextMessage(
                        content=str(model_result.content),
                        source=agent_name,
                    )
                )
                return

            # Step 7: Yield a CodeGenerationEvent
            inferred_text_message: CodeGenerationEvent = CodeGenerationEvent(
                retry_attempt=nth_try,
                content=model_result.content,
                code_blocks=code_blocks,
                source=agent_name,
            )

            yield inferred_text_message

            # Step 8: Execute the extracted code blocks
            execution_result = await self.execute_code_block(inferred_text_message.code_blocks, cancellation_token)

            # Step 9: Update model context with the code execution result
            await model_context.add_message(
                UserMessage(
                    content=execution_result.output,
                    source=agent_name,
                )
            )

            # Step 10: Yield a CodeExecutionEvent
            yield CodeExecutionEvent(retry_attempt=nth_try, result=execution_result, source=self.name)

            # If execution was successful or last retry, then exit
            if execution_result.exit_code == 0 or nth_try == max_retries_on_error:
                break

            # Step 11: If exit code is non-zero and retries are available then
            #          make an inference asking if we should retry or not
            chat_context = await model_context.get_messages()

            retry_prompt = (
                f"The most recent code execution resulted in an error:\n{execution_result.output}\n\n"
                "Should we attempt to resolve it? Please respond with:\n"
                "- A boolean value for 'retry' indicating whether it should be retried.\n"
                "- A detailed explanation in 'reason' that identifies the issue, justifies your decision to retry or not, and outlines how you would resolve the error if a retry is attempted."
            )

            chat_context = chat_context + [
                UserMessage(
                    content=retry_prompt,
                    source=agent_name,
                )
            ]

            response = await model_client.create(messages=chat_context, json_output=RetryDecision)

            assert isinstance(
                response.content, str
            ), "Expected structured response for retry decision to be of type str."
            should_retry_generation = RetryDecision.model_validate_json(str(response.content))

            # Exit if no-retry is needed
            if not should_retry_generation.retry:
                break

            yield CodeGenerationEvent(
                retry_attempt=nth_try,
                content=f"Attempt number: {nth_try + 1}\nProposed correction: {should_retry_generation.reason}",
                code_blocks=[],
                source=agent_name,
            )

        # Always reflect on the execution result
        async for reflection_response in CodeExecutorAgent._reflect_on_code_block_results_flow(
            system_messages=system_messages,
            model_client=model_client,
            model_client_stream=model_client_stream,
            model_context=model_context,
            agent_name=agent_name,
            inner_messages=inner_messages,
        ):
            yield reflection_response  # Last reflection_response is of type Response so it will finish the routine

    async def extract_code_blocks_from_messages(self, messages: Sequence[BaseChatMessage]) -> List[CodeBlock]:
        # Extract code blocks from the messages.
        code_blocks: List[CodeBlock] = []
        for msg in messages:
            if self._sources is None or msg.source in self._sources:
                if isinstance(msg, TextMessage):
                    code_blocks.extend(self._extract_markdown_code_blocks(msg.content))
                # TODO: handle other message types if needed
        return code_blocks

    async def execute_code_block(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        # Execute the code blocks.
        result = await self._code_executor.execute_code_blocks(code_blocks, cancellation_token=cancellation_token)

        if result.output.strip() == "":
            # No output
            result.output = f"The script ran but produced no output to console. The POSIX exit code was: {result.exit_code}. If you were expecting output, consider revising the script to ensure content is printed to stdout."
        elif result.exit_code != 0:
            # Error
            result.output = f"The script ran, then exited with an error (POSIX exit code: {result.exit_code})\nIts output was:\n{result.output}"

        return result

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Its a no-op as the code executor agent has no mutable state."""
        pass

    def _extract_markdown_code_blocks(self, markdown_text: str) -> List[CodeBlock]:
        pattern = re.compile(rf"```(?:\s*({self._supported_languages_regex}))\n([\s\S]*?)```", re.IGNORECASE)
        matches = pattern.findall(markdown_text)
        code_blocks: List[CodeBlock] = []
        for match in matches:
            language = match[0].strip() if match[0] else ""
            code_content = match[1]
            code_blocks.append(CodeBlock(code=code_content, language=language))
        return code_blocks

    def _to_config(self) -> CodeExecutorAgentConfig:
        return CodeExecutorAgentConfig(
            name=self.name,
            model_client=(self._model_client.dump_component() if self._model_client is not None else None),
            code_executor=self._code_executor.dump_component(),
            description=self.description,
            sources=list(self._sources) if self._sources is not None else None,
            system_message=(
                self._system_messages[0].content
                if self._system_messages and isinstance(self._system_messages[0].content, str)
                else None
            ),
            model_client_stream=self._model_client_stream,
            model_context=self._model_context.dump_component(),
            supported_languages=self._supported_languages,
        )

    @classmethod
    def _from_config(cls, config: CodeExecutorAgentConfig) -> Self:
        return cls(
            name=config.name,
            model_client=(
                ChatCompletionClient.load_component(config.model_client) if config.model_client is not None else None
            ),
            code_executor=CodeExecutor.load_component(config.code_executor),
            description=config.description,
            sources=config.sources,
            system_message=config.system_message,
            model_client_stream=config.model_client_stream,
            model_context=ChatCompletionContext.load_component(config.model_context) if config.model_context else None,
            supported_languages=config.supported_languages,
        )

    @staticmethod
    def _get_compatible_context(model_client: ChatCompletionClient, messages: List[LLMMessage]) -> Sequence[LLMMessage]:
        """Ensure that the messages are compatible with the underlying client, by removing images if needed."""
        if model_client.model_info["vision"]:
            return messages
        else:
            return remove_images(messages)

    @classmethod
    async def _call_llm(
        cls,
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        system_messages: List[SystemMessage],
        model_context: ChatCompletionContext,
        agent_name: str,
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[Union[CreateResult, ModelClientStreamingChunkEvent], None]:
        """
        Perform a model inference and yield either streaming chunk events or the final CreateResult.
        """
        all_messages = await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=system_messages + all_messages)

        if model_client_stream:
            model_result: Optional[CreateResult] = None
            async for chunk in model_client.create_stream(
                llm_messages, tools=[], cancellation_token=cancellation_token
            ):
                if isinstance(chunk, CreateResult):
                    model_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
            if model_result is None:
                raise RuntimeError("No final model result in streaming mode.")
            yield model_result
        else:
            model_result = await model_client.create(llm_messages, tools=[], cancellation_token=cancellation_token)
            yield model_result

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[BaseChatMessage],
    ) -> None:
        """
        Add incoming messages to the model context.
        """
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                for llm_msg in msg.context:
                    await model_context.add_message(llm_msg)
            await model_context.add_message(msg.to_model_message())

    @classmethod
    async def _reflect_on_code_block_results_flow(
        cls,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        model_client_stream: bool,
        model_context: ChatCompletionContext,
        agent_name: str,
        inner_messages: List[BaseAgentEvent | BaseChatMessage],
    ) -> AsyncGenerator[Response | ModelClientStreamingChunkEvent | ThoughtEvent, None]:
        """
        If reflect_on_code_block_results=True, we do another inference based on tool results
        and yield the final text response (or streaming chunks).
        """
        all_messages = system_messages + await model_context.get_messages()
        llm_messages = cls._get_compatible_context(model_client=model_client, messages=all_messages)

        reflection_result: Optional[CreateResult] = None

        if model_client_stream:
            async for chunk in model_client.create_stream(llm_messages):
                if isinstance(chunk, CreateResult):
                    reflection_result = chunk
                elif isinstance(chunk, str):
                    yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                else:
                    raise RuntimeError(f"Invalid chunk type: {type(chunk)}")
        else:
            reflection_result = await model_client.create(llm_messages)

        if not reflection_result or not isinstance(reflection_result.content, str):
            raise RuntimeError("Reflect on tool use produced no valid text response.")

        # --- NEW: If the reflection produced a thought, yield it ---
        if reflection_result.thought:
            thought_event = ThoughtEvent(content=reflection_result.thought, source=agent_name)
            yield thought_event
            inner_messages.append(thought_event)

        # Add to context (including thought if present)
        await model_context.add_message(
            AssistantMessage(
                content=reflection_result.content,
                source=agent_name,
                thought=getattr(reflection_result, "thought", None),
            )
        )

        yield Response(
            chat_message=TextMessage(
                content=reflection_result.content,
                source=agent_name,
                models_usage=reflection_result.usage,
            ),
            inner_messages=inner_messages,
        )
