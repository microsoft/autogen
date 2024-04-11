import json
import logging
from typing import List, Optional

from typing_extensions import Literal

from ...coding.base import CodeExecutor
from ..agent import Agent, GenerateReplyResult
from ..types import (
    AssistantMessage,
    FunctionCall,
    FunctionCallMessage,
    FunctionCallResult,
    MessageAndSender,
    UserMessage,
)

logger = logging.getLogger(__name__)


class CodeExecutionAgent(Agent):
    def __init__(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        code_executor: CodeExecutor,
        # Max messages to lookback for either code or unexecuted tool calls
        max_lookback: Optional[int] = None,
        handle_function_missing: Literal["ignore", "error"] = "ignore",
    ):
        self._name = name

        self._description = ""
        if description is not None:
            self._description = description

        self._code_executor = code_executor
        self._max_lookback = max_lookback
        self._handle_function_missing = handle_function_missing

    @property
    def name(self) -> str:
        """Get the name of the agent."""
        return self._name

    @property
    def description(self) -> str:
        """Get the description of the agent."""
        return self._description

    @property
    def code_executor(self) -> CodeExecutor:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        return self._code_executor

    async def handle_function_calls(
        self,
        function_calls: List[FunctionCall],
    ) -> FunctionCallMessage:
        return FunctionCallMessage(
            call_results=[
                FunctionCallResult(
                    content=self._code_executor.execute_function(x.name, json.loads(x.arguments)), call_id=x.id
                )
                for x in function_calls
            ]
        )

    async def generate_reply(
        self,
        messages: List[MessageAndSender],
    ) -> GenerateReplyResult:
        # Find the last message that contains either code, or unexecuted tool calls up to max lookback
        if self._max_lookback is not None:
            messages_to_scan = messages[-self._max_lookback :]
        else:
            messages_to_scan = messages

        called_ids: List[str] = []
        for message in reversed(messages_to_scan):
            if isinstance(message, FunctionCallMessage):
                for result in message.call_results:
                    called_ids.append(result.call_id)

            if isinstance(message, AssistantMessage):
                if message.content is None and message.function_calls is None:
                    raise ValueError("AssistantMessage must have content or function_calls")

                if message.function_calls is not None:
                    return await self.handle_function_calls(message.function_calls)

                code_blocks = self._code_executor.code_extractor.extract_code_blocks(message.content)
                if len(code_blocks) == 0:
                    continue
                # found code blocks, execute code.
                code_result = self._code_executor.execute_code_blocks(code_blocks)
                exitcode2str = "execution succeeded" if code_result.exit_code == 0 else "execution failed"
                return UserMessage(
                    content=f"exitcode: {code_result.exit_code} ({exitcode2str})\nCode output: {code_result.output}"
                )

        return UserMessage(content="No function or code block found to execute")
