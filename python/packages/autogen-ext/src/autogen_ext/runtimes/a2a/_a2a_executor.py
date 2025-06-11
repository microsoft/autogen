from asyncio import CancelledError, iscoroutinefunction

from typing import Callable, Awaitable, Union

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, Task, TextPart, Part
from a2a.utils import new_task
from autogen_agentchat.base import TaskResult, ChatAgent, Team
from autogen_agentchat.messages import UserInputRequestedEvent, TextMessage

from autogen_core import CancellationToken, CacheStore, InMemoryStore

from ._a2a_execution_context import A2aExecutionContext
from ._a2a_event_adapter import A2aEventAdapter, BaseA2aEventAdapter
from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent

SyncGetAgentFuncType = Callable[[A2aExecutionContext], Union[ChatAgent, Team]]
AsyncGetAgentFuncType = Callable[[A2aExecutionContext], Awaitable[Union[ChatAgent, Team]]]
GetAgentFuncType = Union[SyncGetAgentFuncType, AsyncGetAgentFuncType]

class A2aExecutor(AgentExecutor):
    def __init__(self, get_agent: GetAgentFuncType,
                 event_adapter: A2aEventAdapter = BaseA2aEventAdapter(), state_store: CacheStore = None):
        super().__init__()
        self._cancellation_tokens:dict[str, CancellationToken] = {}
        self._state_store: CacheStore = state_store
        self._get_agent: GetAgentFuncType = get_agent
        self._event_adapter: A2aEventAdapter = event_adapter
        if not self._state_store:
            self._state_store = InMemoryStore()


    def build_context(self, request_context: RequestContext, task: Task, updater: TaskUpdater, user_proxy_agent: A2aExternalUserProxyAgent, cancellation_token: CancellationToken) -> A2aExecutionContext:
        """Get the agent to execute the task."""
        return A2aExecutionContext(request_context, task, updater, user_proxy_agent, cancellation_token)

    def ensure_cancellation_data(self, task: Task):
        """Ensure cancellation data exists for the given task ID."""
        if task.id not in self._cancellation_tokens:
            self._cancellation_tokens[task.id] = CancellationToken()

    def clear_cancellation_data(self, task: Task):
        """Clear cancellation data for the given task ID."""
        if task.id in self._cancellation_tokens:
            del self._cancellation_tokens[task.id]

    async def cancel(self, request_context: RequestContext, event_queue: EventQueue):
        if not request_context.current_task:
            return
        if request_context.current_task.id not in self._cancellation_tokens:
            return
        cancellation_token = self._cancellation_tokens.get(request_context.current_task.id)
        cancellation_token.cancel()

    async def get_stateful_agent(self, context: A2aExecutionContext) -> Union[ChatAgent, Team]:
        if iscoroutinefunction(self._get_agent):
            agent: Union[ChatAgent, Team] = await self._get_agent(context)
        else:
            agent: Union[ChatAgent, Team] = self._get_agent(context)
        existing_state = self._state_store.get(context.task.id)
        if existing_state:
            await agent.load_state(existing_state)
        return agent

    async def execute(self, request_context: RequestContext, event_queue: EventQueue):
        """Execute the agent with the given context and event queue."""
        query = request_context.get_user_input()
        task = request_context.current_task
        if not task:
            task = new_task(request_context.message)
            event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, request_context.context_id)
        updater.submit()

        self.ensure_cancellation_data(task)
        cancellation_token = self._cancellation_tokens[task.id]
        user_proxy_agent = A2aExternalUserProxyAgent()

        execution_context = self.build_context(request_context, task, updater, user_proxy_agent, cancellation_token)
        agent = await self.get_stateful_agent(execution_context)
        try:
            updater.start_work()
            async for message in agent.run_stream(task=TextMessage(content=query, source=user_proxy_agent.name), cancellation_token=cancellation_token):
                if isinstance(message, TaskResult):
                    updater.complete()
                elif isinstance(message, UserInputRequestedEvent):
                    updater.update_status(final=False, state=TaskState.input_required)
                else:
                    self._event_adapter.handle_events(message, execution_context)
        except CancelledError:
            if user_proxy_agent.is_cancelled_by_me:
                updater.update_status(state=TaskState.input_required, final=True)
            else:
                updater.update_status(state=TaskState.canceled, final=True)
        except Exception as e:
            updater.update_status(state=TaskState.failed, final=True, message=updater.new_agent_message([Part(root=TextPart(text=str(e.args)))]))
        finally:
            self.clear_cancellation_data(task)
            self._state_store.set(task.id, await agent.save_state())
