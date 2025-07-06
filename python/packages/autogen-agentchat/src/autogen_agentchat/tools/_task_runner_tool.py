from abc import ABC
from typing import Annotated, Any, AsyncGenerator, List, Mapping

from autogen_core import CancellationToken
from autogen_core.tools import BaseStreamTool
from pydantic import BaseModel

from ..agents import BaseChatAgent
from ..base import TaskResult
from ..messages import BaseAgentEvent, BaseChatMessage
from ..teams import BaseGroupChat


class TaskRunnerToolArgs(BaseModel):
    """Input for the TaskRunnerTool."""

    task: Annotated[str, "The task to be executed."]


class TaskRunnerTool(BaseStreamTool[TaskRunnerToolArgs, BaseAgentEvent | BaseChatMessage, TaskResult], ABC):
    """An base class for tool that can be used to run a task using a team or an agent."""

    component_type = "tool"

    def __init__(
        self,
        task_runner: BaseGroupChat | BaseChatAgent,
        name: str,
        description: str,
        return_value_as_last_message: bool,
    ) -> None:
        self._task_runner = task_runner
        self._return_value_as_last_message = return_value_as_last_message
        super().__init__(
            args_type=TaskRunnerToolArgs,
            return_type=TaskResult,
            name=name,
            description=description,
        )

    async def run(self, args: TaskRunnerToolArgs, cancellation_token: CancellationToken) -> TaskResult:
        """Run the task and return the result."""
        return await self._task_runner.run(task=args.task, cancellation_token=cancellation_token)

    async def run_stream(
        self, args: TaskRunnerToolArgs, cancellation_token: CancellationToken
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """Run the task and yield events or messages as they are produced, the final :class:`TaskResult`
        will be yielded at the end."""
        async for event in self._task_runner.run_stream(task=args.task, cancellation_token=cancellation_token):
            yield event

    def return_value_as_string(self, value: TaskResult) -> str:
        """Convert the task result to a string."""
        if self._return_value_as_last_message:
            if value.messages and isinstance(value.messages[-1], BaseChatMessage):
                return value.messages[-1].to_model_text()
            raise ValueError("The last message is not a BaseChatMessage.")
        parts: List[str] = []
        for message in value.messages:
            if isinstance(message, BaseChatMessage):
                if message.source == "user":
                    continue
                parts.append(f"{message.source}: {message.to_model_text()}")
        return "\n\n".join(parts)

    async def save_state_json(self) -> Mapping[str, Any]:
        return await self._task_runner.save_state()

    async def load_state_json(self, state: Mapping[str, Any]) -> None:
        await self._task_runner.load_state(state)
