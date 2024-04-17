import inspect
import logging
from typing import Awaitable, Callable, List, Optional, Sequence, Union, cast

from ...coding.base import CodeExecutor
from ..agent import Agent
from ..chat_history import ChatHistoryReadOnly
from ..types import AssistantMessage, GenerateReplyResult, Message, UserMessage

__all__ = ("UserProxyAgent",)

ReplyFunctionAsync = Callable[["UserProxyAgent", Sequence[Message]], Awaitable[Optional[Message]]]
ReplyFunctionSync = Callable[["UserProxyAgent", Sequence[Message]], Optional[Message]]
ReplyFunction = Union[ReplyFunctionAsync, ReplyFunctionSync]
HumanInputCallback = Callable[[str], Awaitable[str]]

# async def async_human_input(prompt: str) -> str:
#     return await ainput(prompt)

logger = logging.getLogger(__name__)


class UserProxyAgent(Agent):
    def __init__(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        code_executor: Optional[CodeExecutor] = None,
        human_input_callback: Optional[HumanInputCallback] = None,
    ):
        self._name = name

        if description is not None:
            self._description = description
        else:
            """"""

        self._reply_func_list: List[ReplyFunction] = []
        self._human_input_callback = human_input_callback
        if self._human_input_callback is not None:
            self._reply_func_list.append(UserProxyAgent.get_human_reply)

        self._code_executor = code_executor
        if self._code_executor is not None:
            self._reply_func_list.append(UserProxyAgent._generate_code_execution_reply_using_executor)

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    @property
    def code_executor(self) -> Optional[CodeExecutor]:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        return self._code_executor

    def _generate_code_execution_reply_using_executor(
        self,
        messages: Sequence[Message],
    ) -> Optional[UserMessage]:
        """Generate a reply using code executor."""
        # Only added to generate reply if this is not none
        assert self._code_executor is not None, "Code executor is not provided."

        last_n_messages_or_auto = "auto"
        # TODO last n messages
        # if (
        #     not (isinstance(last_n_messages_or_auto, (int, float)) and last_n_messages_or_auto >= 0)
        #     and last_n_messages_or_auto != "auto"
        # ):
        #     raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

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
        messages: Sequence[Message],
    ) -> Optional[UserMessage]:

        assert self._human_input_callback is not None, "Human input callback is not provided."

        reply = await self._human_input_callback(
            "Provide feedback. Press enter to skip and use auto-reply, or type 'exit' to end the conversation: "
        )

        if reply == "":
            return None

        if reply.lower() == "exit":
            return UserMessage(content=reply, is_termination=True)

        return UserMessage(content=reply)

    async def generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:
        messages = chat_history.messages
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
