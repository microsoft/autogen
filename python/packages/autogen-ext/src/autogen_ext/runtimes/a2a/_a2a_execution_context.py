from a2a.server.agent_execution import RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import Task
from autogen_core import CancellationToken
from pydantic import BaseModel

from ._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent


class A2aExecutionContext(BaseModel):
    """
    A2aExecutorContext is a class that provides a context for executing A2A (Ask to Answer) tasks.
    It contains the necessary information and methods to manage the execution of A2A tasks.
    """
    streaming_chunks_id: str | None = None

    def __init__(self, request: RequestContext, task: Task, updater: TaskUpdater, user_proxy_agent: A2aExternalUserProxyAgent,
                 cancellation_token: CancellationToken):
        super().__init__(streaming_chunks_id=None)
        self._task = task
        self._updater = updater
        self._user_proxy_agent = user_proxy_agent
        self._request = request
        self._cancellation_token = cancellation_token

    @property
    def updater(self) -> TaskUpdater:
        """
        Returns the TaskUpdater instance associated with this context.
        """
        return self._updater

    @property
    def user_proxy_agent(self) -> A2aExternalUserProxyAgent:
        """
        Returns the A2aExternalUserProxyAgent instance associated with this context.
        """
        return self._user_proxy_agent

    @property
    def request(self) -> RequestContext:
        """
        Returns the RequestContext instance associated with this context.
        """
        return self._request

    @property
    def cancellation_token(self) -> CancellationToken:
        """
        Returns the CancellationToken instance associated with this context.
        This token can be used to cancel the task execution.
        """
        return self._cancellation_token

    @property
    def task(self) -> Task:
        """
        Returns the Task instance associated with this context.
        """
        return self._task

