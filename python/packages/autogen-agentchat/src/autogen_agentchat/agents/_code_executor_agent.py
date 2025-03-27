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
from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_core.memory import Memory
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
    AgentEvent,
    ChatMessage,
    HandoffMessage,
    MemoryQueryEvent,
    ModelClientStreamingChunkEvent,
    TextMessage,
    ThoughtEvent,
)
from ..utils import remove_images
from ._base_chat_agent import BaseChatAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)

DEFAULT_TERMINAL_DESCRIPTION = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks)."

DEFAULT_AGENT_DESCRIPTION = "A Code Execution Agent that generates and executes Python and shell scripts based on user instructions. Python code should be provided in ```python code blocks, and sh shell scripts should be provided in ```sh code blocks for execution. It ensures correctness, efficiency, and minimal errors while gracefully handling edge cases."

DEFAULT_SYSTEM_MESSAGE = "You are a Code Execution Agent. Your role is to generate and execute Python code based on user instructions, ensuring correctness, efficiency, and minimal errors. Handle edge cases gracefully."


class CodeExecutorAgentConfig(BaseModel):
    """Configuration for CodeExecutorAgent"""

    name: str
    code_executor: ComponentModel
    model_client: ComponentModel | None
    description: str | None = None
    sources: List[str] | None = None
    system_message: str | None = None
    model_client_stream: bool = False
    model_context: ComponentModel | None = None


class CodeExecutorAgent(BaseChatAgent, Component[CodeExecutorAgentConfig]):
    """An agent that extracts and executes code snippets found in received messages and returns the output.

    It is typically used within a team with another agent that generates code snippets to be executed.

    .. note::

        Consider :class:`~autogen_ext.tools.code_execution.PythonCodeExecutionTool`
        as an alternative to this agent. The tool allows for executing Python code
        within a single agent, rather than sending it to a separate agent for execution.
        However, the model for the agent will have to generate properly escaped code
        string as a parameter to the tool.

    Args:
        name: The name of the agent.
        code_executor: The CodeExecutor responsible for executing code received in messages (:py:class:`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` recommended. See example below)
        description (optional): The description of the agent.
        sources (optional): Check only messages from the specified agents for the code to execute.


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

    """

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
        description: str | None = None,
        system_message: str | None = DEFAULT_SYSTEM_MESSAGE,
        sources: Sequence[str] | None = None,
    ) -> None:
        if description is None:
            if model_client is None:
                description = DEFAULT_TERMINAL_DESCRIPTION
            else:
                description = DEFAULT_AGENT_DESCRIPTION

        super().__init__(name=name, description=description)
        self._code_executor = code_executor
        self._sources = sources

        self._model_client = None
        if model_client is not None:
            self._model_client = model_client
            self._model_client_stream = model_client_stream

        if model_context is not None:
            self._model_context = model_context
        else:
            self._model_context = UnboundedChatCompletionContext()

        self._system_messaages: List[SystemMessage] = []
        if system_message is None:
            self._system_messages = []
        else:
            self._system_messages = [SystemMessage(content=system_message)]

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        """The types of messages that the code executor agent produces."""
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentEvent | ChatMessage | Response, None]:
        """
        Process the incoming messages with the assistant agent and yield events/responses as they happen.
        """

        # Gather all relevant state here
        agent_name = self.name
        model_context = self._model_context
        system_messages = self._system_messages
        model_client = self._model_client
        model_client_stream = self._model_client_stream

        if model_client is not None:
            # STEP 1: Add new user/handoff messages to the model context
            await self._add_messages_to_context(
                model_context=model_context,
                messages=messages,
            )

            # STEP 2: Update model context with any relevant memory
            inner_messages: List[AgentEvent | ChatMessage] = []
            for event_msg in await self._update_model_context_with_memory(
                memory=None,
                model_context=model_context,
                agent_name=agent_name,
            ):
                inner_messages.append(event_msg)
                yield event_msg

            # STEP 3: Run the first inference
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

            # --- NEW: If the model produced a hidden "thought," yield it as an event ---
            if model_result.thought:
                thought_event = ThoughtEvent(content=model_result.thought, source=agent_name)
                yield thought_event
                inner_messages.append(thought_event)

            # Add the assistant message to the model context (including thought if present)
            await model_context.add_message(
                AssistantMessage(
                    content=model_result.content,
                    source=agent_name,
                    thought=getattr(model_result, "thought", None),
                )
            )

            # NOTE: error: Argument of type "str | List[FunctionCall]" cannot be assigned to parameter "content" of type "str" in function "__init__".
            #       For now we can assume that there are no FunctionCalls in the response because we are not providing tools to the CodeExecutorAgent.
            #       So, for now we cast model_result.content to string
            inferred_text_message: TextMessage = TextMessage(content=str(model_result.content), source=agent_name)

            # execute generated code if present
            execution_result: Response = await self.execute_code_block([inferred_text_message], cancellation_token)

            # TODO: need a better way to bypass yielding in case there are no code blocks from the code executor.
            if (
                execution_result.chat_message.content
                != "No code blocks found in the thread. Please provide at least one markdown-encoded code block to execute (i.e., quoting code in ```python or ```sh code blocks)."
            ):
                # if code block present then yield inferred_text_message as TextMessage
                # and execution_result as Response
                yield inferred_text_message
                yield execution_result
            else:
                # else yield inferred_text_message as Response
                yield Response(chat_message=inferred_text_message)

        else:  # default behaviour for backward compatibility
            # execute generated code if present
            execution_result = await self.execute_code_block(messages, cancellation_token)
            yield execution_result

    async def execute_code_block(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> Response:
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

    def _to_config(self) -> CodeExecutorAgentConfig:
        return CodeExecutorAgentConfig(
            name=self.name,
            model_client=self._model_client.dump_component() if self._model_client is not None else None,
            code_executor=self._code_executor.dump_component(),
            description=self.description,
            sources=list(self._sources) if self._sources is not None else None,
            system_message=self._system_messages[0].content
            if self._system_messages and isinstance(self._system_messages[0].content, str)
            else None,
            model_client_stream=self._model_client_stream,
            model_context=self._model_context.dump_component(),
        )

    @classmethod
    def _from_config(cls, config: CodeExecutorAgentConfig) -> Self:
        return cls(
            name=config.name,
            model_client=ChatCompletionClient.load_component(config.model_client)
            if config.model_client is not None
            else None,
            code_executor=CodeExecutor.load_component(config.code_executor),
            description=config.description,
            sources=config.sources,
            system_message=config.system_message,
            model_client_stream=config.model_client_stream,
            model_context=None,
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
    async def _update_model_context_with_memory(
        memory: Optional[Sequence[Memory]],
        model_context: ChatCompletionContext,
        agent_name: str,
    ) -> List[MemoryQueryEvent]:
        """
        If memory modules are present, update the model context and return the events produced.
        """
        events: List[MemoryQueryEvent] = []
        if memory:
            for mem in memory:
                update_context_result = await mem.update_context(model_context)
                if update_context_result and len(update_context_result.memories.results) > 0:
                    memory_query_event_msg = MemoryQueryEvent(
                        content=update_context_result.memories.results,
                        source=agent_name,
                    )
                    events.append(memory_query_event_msg)
        return events

    @staticmethod
    async def _add_messages_to_context(
        model_context: ChatCompletionContext,
        messages: Sequence[ChatMessage],
    ) -> None:
        """
        Add incoming user (and possibly handoff) messages to the model context.
        """
        for msg in messages:
            if isinstance(msg, HandoffMessage):
                # Add handoff context to the model context.
                for context_msg in msg.context:
                    await model_context.add_message(context_msg)
            await model_context.add_message(UserMessage(content=msg.content, source=msg.source))
