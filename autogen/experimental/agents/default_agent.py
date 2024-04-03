import inspect
import logging
from typing import Awaitable, Callable, List, Optional, Tuple, Union, cast


from ..model_client import ChatModelClient
from ..types import AssistantMessage, ChatMessage, SystemMessage, UserMessage

from ...cache import AbstractCache

from ...coding.base import CodeExecutor
from ..agent import Agent

__all__ = ("DefaultAgent",)

ReplyFunctionAsync = Callable[["DefaultAgent", List[ChatMessage]], Awaitable[Optional[ChatMessage]]]
ReplyFunctionSync = Callable[["DefaultAgent", List[ChatMessage]], Optional[ChatMessage]]
ReplyFunction = Union[ReplyFunctionAsync, ReplyFunctionSync]
HumanInputCallback = Callable[[str], Awaitable[str]]

# async def async_human_input(prompt: str) -> str:
#     return await ainput(prompt)

logger = logging.getLogger(__name__)


class DefaultAgent(Agent):
    _code_executor: Optional[CodeExecutor]
    _human_input_callback: Optional[HumanInputCallback]
    _model_client: Optional[ChatModelClient]
    _system_message: Optional[SystemMessage]
    _cache: Optional[AbstractCache]
    _reply_func_list: List[ReplyFunction]

    def __init__(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        system_message: Optional[str] = "You are a helpful AI Assistant.",
        code_executor: Optional[CodeExecutor] = None,
        model_client: Optional[ChatModelClient] = None,
        human_input_callback: Optional[HumanInputCallback] = None,
        cache: Optional[AbstractCache] = None,
    ):
        self._name = name
        self._system_message = SystemMessage(content=system_message) if system_message is not None else None

        if description is not None:
            self._description = description
        elif system_message is not None:
            self._description = system_message
        else:
            """"""

        self._cache = cache

        self._reply_func_list: List[ReplyFunction] = []
        self._human_input_callback = human_input_callback
        if self._human_input_callback is not None:
            self._reply_func_list.append(DefaultAgent.get_human_reply)

        self._model_client = model_client
        if self._model_client is not None:
            self._reply_func_list.append(DefaultAgent.generate_oai_reply)

        self._code_executor = code_executor
        if self._code_executor is not None:
            self._reply_func_list.append(DefaultAgent._generate_code_execution_reply_using_executor)

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    @description.setter
    def description(self, description: str) -> None:
        """Set the description of the agent."""
        self._description = description

    @property
    def code_executor(self) -> Optional[CodeExecutor]:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        return self._code_executor

    @property
    def system_message(self) -> Optional[str]:
        """Return the system message."""
        return self._system_message.content if self._system_message is not None else None

    async def generate_oai_reply(
        self,
        messages: List[ChatMessage],
    ) -> Optional[AssistantMessage]:
        # Should only be called when valid model_client is provided.
        # This is checked in the constructor
        assert self._model_client is not None, "Model client is not provided."

        # TODO support tools
        all_messages: List[ChatMessage] = []
        if self._system_message is not None:
            all_messages.append(self._system_message)
        all_messages.extend(messages)
        response = await self._model_client.create(all_messages, self._cache)
        if isinstance(response.content, str):
            return AssistantMessage(content=response.content)
        else:
            raise NotImplementedError("Tools not supported yet.")
            # return True, AssistantMessage(tool_calls=response.content)

    def _generate_code_execution_reply_using_executor(
        self,
        messages: List[ChatMessage],
    ) -> Optional[UserMessage]:
        """Generate a reply using code executor."""
        # Only added to generate reply if this is not none
        assert self._code_executor is not None, "Code executor is not provided."

        last_n_messages_or_auto = "auto"
        if (
            not (isinstance(last_n_messages_or_auto, (int, float)) and last_n_messages_or_auto >= 0)
            and last_n_messages_or_auto != "auto"
        ):
            raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

        if last_n_messages_or_auto == "auto":
            # Find when the agent last spoke
            num_messages_to_scan = 0
            for message in reversed(messages):
                if isinstance(message, AssistantMessage):
                    break
                else:
                    num_messages_to_scan += 1
        else:
            num_messages_to_scan = int(last_n_messages_or_auto)

        num_messages_to_scan = min(len(messages), num_messages_to_scan)
        messages_to_scan = messages[-num_messages_to_scan:]

        # iterate through the last n messages in reverse
        # if code blocks are found, execute the code blocks and return the output
        # if no code blocks are found, continue
        for message in reversed(messages_to_scan):
            if isinstance(message, AssistantMessage):
                if message.content is None:
                    continue
                code_blocks = self._code_executor.code_extractor.extract_code_blocks(message.content)
                if len(code_blocks) == 0:
                    continue
                # found code blocks, execute code.
                code_result = self._code_executor.execute_code_blocks(code_blocks)
                exitcode2str = "execution succeeded" if code_result.exit_code == 0 else "execution failed"
                return UserMessage(
                    content=f"exitcode: {code_result.exit_code} ({exitcode2str})\nCode output: {code_result.output}"
                )

        return None

    async def get_human_reply(
        self,
        messages: List[ChatMessage],
    ) -> Optional[UserMessage]:

        assert self._human_input_callback is not None, "Human input callback is not provided."

        reply = await self._human_input_callback(
            f"Provide feedback. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
        )

        if reply == "":
            return None

        if reply.lower() == "exit":
            return UserMessage(content=reply, is_termination=True)

        return UserMessage(content=reply)

    async def generate_reply(
        self,
        messages: List[ChatMessage],
    ) -> ChatMessage:

        for reply_func in self._reply_func_list:
            if inspect.iscoroutinefunction(reply_func):
                reply_func = cast(ReplyFunctionAsync, reply_func)
                reply = await reply_func(self, messages)
            else:
                reply_func = cast(ReplyFunctionSync, reply_func)
                reply = reply_func(self, messages)

            if reply is not None:
                return reply
        else:
            # TODO add a default reply
            return AssistantMessage(content="I am not sure how to respond to that.")

    def reset(self) -> None:
        """Reset the agent's state."""
        pass
