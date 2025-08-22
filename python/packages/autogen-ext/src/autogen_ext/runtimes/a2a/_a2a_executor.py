from asyncio import CancelledError, iscoroutinefunction
from typing import Any, Awaitable, Callable, Mapping, Optional, Union

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, Task, TaskState, TextPart
from a2a.utils import new_task
from autogen_agentchat.base import ChatAgent, TaskResult, Team
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent
from autogen_core import CacheStore, CancellationToken, InMemoryStore

from ._a2a_event_adapter import A2aEventAdapter, BaseA2aEventAdapter
from ._a2a_execution_context import A2aExecutionContext
from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent

SyncGetAgentFuncType = Callable[[A2aExecutionContext], Union[ChatAgent, Team]]
AsyncGetAgentFuncType = Callable[[A2aExecutionContext], Awaitable[Union[ChatAgent, Team]]]
GetAgentFuncType = Union[SyncGetAgentFuncType, AsyncGetAgentFuncType]


class A2aExecutor(AgentExecutor):
    """A2A protocol executor for AutoGen agents.

    This executor manages the lifecycle of AutoGen agents in an A2A protocol environment,
    handling message processing, state management, and event adaptation.

    The executor can be customized through several components:
    1. Event Adapter: Controls how AutoGen messages are converted to A2A events
    2. External User Agent: Handles user interaction and input
    3. State Store: Manages persistence of agent state
    4. Agent Factory: Creates agents for task execution

    Args:
        get_agent (GetAgentFuncType): Function that creates the AutoGen agent/team
        event_adapter (A2aEventAdapter): Adapter for event conversion (default: BaseA2aEventAdapter)
        state_store (CacheStore): Store for agent state persistence (default: InMemoryStore)

    Example:
        Basic setup with A2AStarletteApplication:
        ```python
        from a2a.server.apps import A2AStarletteApplication
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.types import AgentCard, AgentCapabilities
        from autogen_ext.runtimes.a2a import A2aExecutor


        # Define agent creation function
        async def get_my_agent(context):
            agent = AssistantAgent(name="MyAgent", system_message="You are a helpful assistant", model_client=llm_client)
            return agent


        # Create executor with custom components
        executor = A2aExecutor(
            get_agent=get_my_agent,
            event_adapter=CustomEventAdapter(),  # Optional
            state_store=RedisStateStore(),  # Optional
        )

        # Setup A2A server
        agent_card = AgentCard(
            name="My A2A Agent",
            description="A helpful assistant",
            capabilities=AgentCapabilities(streaming=True),
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
        )

        handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

        app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler).build()

        # Run the server
        uvicorn.run(app, host="0.0.0.0", port=8000)
        ```

    Customization Examples:
        Custom Event Adapter:
        ```python
        class CustomEventAdapter(A2aEventAdapter):
            def handle_events(self, message, context):
                if isinstance(message, TextMessage):
                    # Custom handling of text messages
                    context.updater.update_status(
                        state=TaskState.working,
                        message=context.updater.new_agent_message(
                            [Part(root=TextPart(text=f"Processed: {message.content}"))]
                        ),
                    )
        ```

        Custom User Proxy:
        ```python
        class CustomUserProxy(A2aExternalUserProxyAgent):
            async def cancel_for_user_input(self, prompt, token):
                # Custom input handling
                result = await external_service.get_input(prompt)
                return result

            def build_context(self, request, task, updater, proxy, token):
                # Use custom user proxy
                proxy = CustomUserProxy()
                return A2aExecutionContext(request, task, updater, proxy, token)
        ```

        Custom State Store:
        ```python
        class RedisStateStore(CacheStore):
            def __init__(self, redis_client):
                self.redis = redis_client

            def get(self, key: str) -> Any:
                return json.loads(self.redis.get(key))

            def set(self, key: str, value: Any):
                self.redis.set(key, json.dumps(value))
        ```

    Note:
        - The executor maintains task cancellation tokens
        - Supports both sync and async agent factory functions
        - Handles proper cleanup of resources
        - Manages agent state persistence
    """

    def __init__(
        self,
        get_agent: GetAgentFuncType,
        event_adapter: Optional[A2aEventAdapter] = None,
        state_store: Optional[CacheStore[Mapping[str, Any]]] = None,
    ):
        super().__init__()
        self._cancellation_tokens: dict[str, CancellationToken] = {}
        self._state_store: CacheStore[Mapping[str, Any]] = state_store if state_store else InMemoryStore()
        self._get_agent: GetAgentFuncType = get_agent
        self._event_adapter: A2aEventAdapter = event_adapter if event_adapter else BaseA2aEventAdapter()

    def build_context(
        self,
        request_context: RequestContext,
        task: Task,
        updater: TaskUpdater,
        user_proxy_agent: A2aExternalUserProxyAgent,
        cancellation_token: CancellationToken,
    ) -> A2aExecutionContext:
        """Get the agent to execute the task."""
        return A2aExecutionContext(request_context, task, updater, user_proxy_agent, cancellation_token)

    def ensure_cancellation_data(self, task: Task) -> None:
        """Ensure cancellation data exists for the given task ID."""
        if task.id not in self._cancellation_tokens:
            self._cancellation_tokens[task.id] = CancellationToken()

    def clear_cancellation_data(self, task: Task) -> None:
        """Clear cancellation data for the given task ID."""
        if task.id in self._cancellation_tokens:
            del self._cancellation_tokens[task.id]

    async def cancel(self, request_context: RequestContext, event_queue: EventQueue) -> None:
        if not request_context.current_task:
            return
        if request_context.current_task.id not in self._cancellation_tokens:
            return
        cancellation_token = self._cancellation_tokens.get(request_context.current_task.id)
        assert cancellation_token
        cancellation_token.cancel()

    async def get_stateful_agent(self, context: A2aExecutionContext) -> Union[ChatAgent, Team]:
        if iscoroutinefunction(self._get_agent):
            agent: Union[ChatAgent, Team] = await self._get_agent(context)
        else:
            agent = self._get_agent(context)
        existing_state = self._state_store.get(context.task.id)
        if existing_state:
            await agent.load_state(existing_state)
        return agent

    async def execute(self, request_context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent with the given context and event queue."""
        query = request_context.get_user_input()
        task = request_context.current_task
        if not task:
            assert request_context.message
            task = new_task(request_context.message)
            await event_queue.enqueue_event(task)
        assert request_context.context_id

        updater = TaskUpdater(event_queue, task.id, request_context.context_id)
        await updater.submit()

        self.ensure_cancellation_data(task)
        cancellation_token = self._cancellation_tokens[task.id]
        user_proxy_agent = A2aExternalUserProxyAgent()

        execution_context = self.build_context(request_context, task, updater, user_proxy_agent, cancellation_token)
        agent = await self.get_stateful_agent(execution_context)
        try:
            await updater.start_work()
            async for message in agent.run_stream(
                task=TextMessage(content=query, source=user_proxy_agent.name), cancellation_token=cancellation_token
            ):
                if isinstance(message, TaskResult):
                    await updater.complete()
                elif isinstance(message, UserInputRequestedEvent):
                    await updater.update_status(final=False, state=TaskState.input_required)
                else:
                    await self._event_adapter.handle_events(message, execution_context)
        except CancelledError:
            if user_proxy_agent.is_cancelled_by_me:
                await updater.update_status(state=TaskState.input_required, final=True)
            else:
                await updater.update_status(state=TaskState.canceled, final=True)
        except Exception as e:
            await updater.update_status(
                state=TaskState.failed,
                final=True,
                message=updater.new_agent_message([Part(root=TextPart(text=str(e.args)))]),
            )
        finally:
            self.clear_cancellation_data(task)
            self._state_store.set(task.id, await agent.save_state())
