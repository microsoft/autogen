import asyncio
import json
import logging
from typing import Awaitable, List, Optional

from typing_extensions import Literal

from ...coding.base import CodeExecutor
from ..agent import Agent
from ..chat_history import ChatHistoryReadOnly
from ..function_executor import FunctionExecutor
from ..types import (
    FunctionCall,
    FunctionCallMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    GenerateReplyResult,
    MultiModalMessage,
    TextMessage,
)

logger = logging.getLogger(__name__)


class ExecutionAgent(Agent):
    def __init__(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        code_executor: Optional[CodeExecutor],
        function_executor: Optional[FunctionExecutor],
        # Max messages to lookback for either code or unexecuted tool calls
        # None means no limit
        max_lookback: Optional[int] = None,
        handle_function_missing: Literal["ignore", "error"] = "ignore",
    ):
        self._name = name

        self._description = ""
        if description is not None:
            self._description = description

        self._code_executor = code_executor
        self._function_executor = function_executor
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
    def code_executor(self) -> Optional[CodeExecutor]:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        return self._code_executor

    @property
    def function_executor(self) -> Optional[FunctionExecutor]:
        """The code executor used by this agent. Returns None if code execution is disabled."""
        return self._function_executor

    async def handle_function_calls(
        self,
        function_calls: List[FunctionCall],
    ) -> FunctionExecutionResultMessage:
        assert self._function_executor is not None
        calls: List[Awaitable[str]] = []
        ids: List[str] = []
        for call in function_calls:
            if call.name not in self._function_executor.functions:
                if self._handle_function_missing == "error":
                    raise ValueError(f"Function {call.name} is not available for execution")
                else:
                    logger.warning(f"Function {call.name} is not available for execution")
                    continue

            calls.append(self._function_executor.execute_function(call.name, json.loads(call.arguments)))
            ids.append(call.id)

        results = await asyncio.gather(*calls)

        return FunctionExecutionResultMessage(
            [FunctionExecutionResult(content=result, call_id=id) for result, id in zip(results, ids)], source=self.name
        )

    async def generate_reply(
        self,
        chat_history: ChatHistoryReadOnly,
    ) -> GenerateReplyResult:
        # Find the last message that contains either code, or unexecuted tool calls up to max lookback
        messages_to_scan = chat_history.messages
        if self._max_lookback is not None:
            messages_to_scan = messages_to_scan[-self._max_lookback :]

        called_ids: List[str] = []
        for message in reversed(messages_to_scan):
            match message:
                case FunctionExecutionResultMessage(results):
                    for result in results:
                        called_ids.append(result.call_id)
                case TextMessage(content) if self._code_executor is not None:
                    code_blocks = self._code_executor.code_extractor.extract_code_blocks(content)
                    if len(code_blocks) == 0:
                        continue
                    # found code blocks, execute code.
                    code_result = self._code_executor.execute_code_blocks(code_blocks)
                    exitcode2str = "execution succeeded" if code_result.exit_code == 0 else "execution failed"
                    return TextMessage(
                        content=f"exitcode: {code_result.exit_code} ({exitcode2str})\nCode output: {code_result.output}",
                        source=self.name,
                    )
                case MultiModalMessage():
                    # TODO support
                    pass
                case FunctionCallMessage(content) if self._function_executor is not None:
                    return await self.handle_function_calls(content)
                case _:
                    pass

        return TextMessage(content="No function or code block found to execute", source=self.name)
