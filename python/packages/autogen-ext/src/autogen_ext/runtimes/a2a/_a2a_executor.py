from abc import ABC, abstractmethod
from asyncio import CancelledError

from typing import Callable, Awaitable, Union

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState, Task, TextPart, Part
from a2a.utils import new_task
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.base import TaskResult, ChatAgent, Team
from autogen_agentchat.messages import UserInputRequestedEvent, TextMessage

from autogen_core import CancellationToken, CacheStore, InMemoryStore

from ._a2a_serializer import A2aSerializer
from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent

SyncGetAgentFuncType = Callable[[RequestContext, UserProxyAgent, CancellationToken], Union[ChatAgent, Team]]
AsyncGetAgentFuncType = Callable[[RequestContext, UserProxyAgent, CancellationToken], Awaitable[Union[ChatAgent, Team]]]
GetAgentFuncType = Union[SyncGetAgentFuncType, AsyncGetAgentFuncType]

SyncGetEventAdapterType = Callable[[TaskUpdater, RequestContext], A2aSerializer]
AsyncGetEventAdapterType = Callable[[TaskUpdater, RequestContext], Awaitable[A2aSerializer]]
GetEventAdapterType = Union[SyncGetEventAdapterType, AsyncGetEventAdapterType]


class A2aExecutor(AgentExecutor, ABC):

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, state_store: CacheStore = None):
        self.cancellation_tokens:dict[str, CancellationToken] = {}
        self.state_Store = state_store
        if not self.state_Store:
            self.state_Store = InMemoryStore()


    @abstractmethod
    async def get_agent(self, context: RequestContext, user_proxy_agent: UserProxyAgent, cancellation_token: CancellationToken) -> Union[ChatAgent, Team]:
        """Get the agent to execute the task."""
        pass

    async def get_a2a_serializer(self, updater: TaskUpdater, user_proxy_agent: A2aExternalUserProxyAgent, context: RequestContext) -> A2aSerializer:
        """Get the event adapter for handling events."""
        return A2aSerializer(updater, user_proxy_agent)

    def ensure_cancellation_data(self, task: Task):
        """Ensure cancellation data exists for the given task ID."""
        if task.id not in self.cancellation_tokens:
            self.cancellation_tokens[task.id] = CancellationToken()

    def clear_cancellation_data(self, task: Task):
        """Clear cancellation data for the given task ID."""
        if task.id in self.cancellation_tokens:
            del self.cancellation_tokens[task.id]

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        if not context.current_task:
            return
        if context.current_task.id not in self.cancellation_tokens:
            return
        cancellation_token = self.cancellation_tokens.get(context.current_task.id)
        cancellation_token.cancel()

    async def get_stateful_agent(self, context: RequestContext, user_proxy_agent: UserProxyAgent, cancellation_token: CancellationToken) -> Union[ChatAgent, Team]:
        agent = await self.get_agent(context, user_proxy_agent, cancellation_token)
        existing_state = self.state_Store.get(context.task_id)
        if existing_state:
            await agent.load_state(existing_state)
        return agent

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute the agent with the given context and event queue."""
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, context.context_id)
        user_proxy_agent = A2aExternalUserProxyAgent()
        updater.submit()
        self.ensure_cancellation_data(task)
        cancellation_token = self.cancellation_tokens[task.id]
        agent = await self.get_stateful_agent(context, user_proxy_agent, cancellation_token)
        event_adapter = await self.get_a2a_serializer(updater, user_proxy_agent, context)
        try:
            updater.start_work()
            async for message in agent.run_stream(task=TextMessage(content=query, source=user_proxy_agent.name), cancellation_token=cancellation_token):
                if isinstance(message, TaskResult):
                    updater.complete()
                elif isinstance(message, UserInputRequestedEvent):
                    updater.update_status(final=False, state=TaskState.input_required)
                else:
                    event_adapter.handle_events(message)
        except CancelledError:
            if user_proxy_agent.is_cancelled_by_me:
                updater.update_status(state=TaskState.input_required, final=True)
            else:
                updater.update_status(state=TaskState.canceled, final=True)
        except Exception as e:
            updater.update_status(state=TaskState.failed, final=True, message=updater.new_agent_message([Part(root=TextPart(text=str(e.args)))]))
        finally:
            self.clear_cancellation_data(task)
            self.state_Store.set(task.id, await agent.save_state())