from a2a.server.agent_execution import RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import Task
from autogen_core import CancellationToken
from pydantic import BaseModel

from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent


class A2aExecutionContext(BaseModel):
    """Execution context for A2A (Ask to Answer) protocol tasks.

    This class manages the execution context for A2A protocol tasks, providing access to:
    - Task state and updates
    - User proxy agent for interaction
    - Request context for protocol handling
    - Cancellation support
    - Streaming state management

    Args:
        request (RequestContext): The A2A protocol request context
        task (Task): The current task being executed
        updater (TaskUpdater): Task state update manager
        user_proxy_agent (A2aExternalUserProxyAgent): Agent for user interactions
        cancellation_token (CancellationToken): Token for task cancellation

    Attributes:
        streaming_chunks_id (str | None): ID for managing streaming content chunks

    Example:
        ```python
        context = A2aExecutionContext(
            request=request_context,
            task=current_task,
            updater=task_updater,
            user_proxy_agent=proxy_agent,
            cancellation_token=CancellationToken(),
        )

        # Access task updater
        context.updater.update_status(state=TaskState.working)

        # Check for cancellation
        if context.cancellation_token.cancelled:
            return

        # Handle streaming
        context.streaming_chunks_id = "stream_123"
        ```

    Note:
        This context is crucial for maintaining state and coordinating
        between different components of the A2A protocol implementation.
    """

    streaming_chunks_id: str | None = None

    def __init__(
        self,
        request: RequestContext,
        task: Task,
        updater: TaskUpdater,
        user_proxy_agent: A2aExternalUserProxyAgent,
        cancellation_token: CancellationToken,
    ):
        super().__init__(streaming_chunks_id=None)
        self._task = task
        self._updater = updater
        self._user_proxy_agent = user_proxy_agent
        self._request = request
        self._cancellation_token = cancellation_token

    @property
    def updater(self) -> TaskUpdater:
        """Get the task state update manager.

        Returns:
            TaskUpdater: Manager for updating task state and sending events

        Example:
            ```python
            context.updater.update_status(
                state=TaskState.working,
                message=context.updater.new_agent_message([Part(root=TextPart(text="Processing..."))]),
            )
            ```

        Note:
            The TaskUpdater handles:
            - Task state transitions
            - Progress updates
            - Event queueing
            - Message creation
        """
        return self._updater

    @property
    def user_proxy_agent(self) -> A2aExternalUserProxyAgent:
        """Get the external user proxy agent.

        Returns:
            A2aExternalUserProxyAgent: Agent handling user interactions

        Example:
            ```python
            # Check if message is from user
            if message.source == context.user_proxy_agent.name:
                # Handle user message
                pass

            # Get user input
            response = await context.user_proxy_agent.request_input("Need clarification")
            ```

        Note:
            The proxy agent manages:
            - User message handling
            - Input requests
            - User interaction state
            - Message attribution
        """
        return self._user_proxy_agent

    @property
    def request(self) -> RequestContext:
        """Get the A2A protocol request context.

        Returns:
            RequestContext: The protocol-level request context

        Example:
            ```python
            # Access request metadata
            metadata = context.request.metadata

            # Get context ID
            context_id = context.request.context_id

            # Check request parameters
            params = context.request.params
            ```

        Note:
            The request context contains:
            - Protocol metadata
            - Request parameters
            - Session information
            - Context identifiers
        """
        return self._request

    @property
    def cancellation_token(self) -> CancellationToken:
        """Get the task cancellation token.

        Returns:
            CancellationToken: Token for managing task cancellation

        Example:
            ```python
            # Check if task should be cancelled
            if context.cancellation_token.cancelled:
                await cleanup()
                return

            # Register cancellation callback
            context.cancellation_token.register(on_cancel)

            # In a long operation
            async for chunk in stream:
                if context.cancellation_token.cancelled:
                    break
                process(chunk)
            ```

        Note:
            The cancellation token:
            - Enables cooperative task cancellation
            - Supports cancellation callbacks
            - Helps manage resource cleanup
            - Coordinates task termination
        """
        return self._cancellation_token

    @property
    def task(self) -> Task:
        """Get the current task being executed.

        Returns:
            Task: The task instance with its current state

        Example:
            ```python
            # Access task ID
            task_id = context.task.id

            # Check task state
            if context.task.state == TaskState.working:
                # Continue processing
                pass

            # Access task metadata
            metadata = context.task.metadata
            ```

        Note:
            The task object contains:
            - Task identifier
            - Current state
            - Associated metadata
            - Execution history
            - Task parameters
        """
        return self._task
