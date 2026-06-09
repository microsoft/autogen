from typing import AsyncGenerator, Protocol, Sequence

from autogen_core import CancellationToken
from pydantic import BaseModel, SerializeAsAny

from ..messages import BaseAgentEvent, BaseChatMessage


class TaskResult(BaseModel):
    """Result of running a task."""

    messages: Sequence[SerializeAsAny[BaseAgentEvent | BaseChatMessage]]
    """Messages produced by the task."""

    stop_reason: str | None = None
    """The reason the task stopped."""


class TaskRunner(Protocol):
    """A task runner."""

    async def run(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> TaskResult:
        """Run the task and return the result.

        The task can be a string, a single message, or a sequence of messages.

        The runner is stateful and a subsequent call to this method will continue
        from where the previous call left off. If the task is not specified,
        the runner will continue with the current task.

        Args:
            task: The task to run. Can be a string, a single message, or a sequence of messages.
            cancellation_token: The cancellation token to kill the task immediately.
            output_task_messages: Whether to include task messages in :attr:`TaskResult.messages`. Defaults to True for backward compatibility.
        """
        ...

    def run_stream(
        self,
        *,
        task: str | BaseChatMessage | Sequence[BaseChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
        output_task_messages: bool = True,
    ) -> AsyncGenerator[BaseAgentEvent | BaseChatMessage | TaskResult, None]:
        """Run the task and produces a stream of messages and the final result
        :class:`TaskResult` as the last item in the stream.

        The task can be a string, a single message, or a sequence of messages.

        The runner is stateful and a subsequent call to this method will continue
        from where the previous call left off. If the task is not specified,
        the runner will continue with the current task.

        Args:
            task: The task to run. Can be a string, a single message, or a sequence of messages.
            cancellation_token: The cancellation token to kill the task immediately.
            output_task_messages: Whether to include task messages in the output stream. Defaults to True for backward compatibility.
        """
        ...
