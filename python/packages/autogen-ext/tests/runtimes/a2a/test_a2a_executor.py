import uuid
from asyncio import CancelledError
from typing import Any, AsyncGenerator, Awaitable, Callable, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Part, Role, Task, TaskState, TextPart
from autogen_agentchat.base import ChatAgent, TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core import CacheStore, CancellationToken, InMemoryStore
from autogen_ext.runtimes.a2a import A2aExecutionContext
from autogen_ext.runtimes.a2a._a2a_event_adapter import A2aEventAdapter
from autogen_ext.runtimes.a2a._a2a_executor import A2aExecutor
from autogen_ext.runtimes.a2a._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent


def get_mock_agent(messages: Optional[List[TextMessage | TaskResult]] = None) -> MagicMock:
    agent = Mock(spec=ChatAgent)

    async def mock_run_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[TextMessage | TaskResult, None]:
        for message in messages or []:
            yield message

    agent.run_stream = mock_run_stream
    agent.save_state = AsyncMock(return_value={"state": "saved"})
    agent.load_state = AsyncMock()
    return agent


@pytest.fixture
def event_queue() -> MagicMock:
    queue = Mock(spec=EventQueue)
    queue.enqueue_event = AsyncMock()
    return queue


@pytest.fixture
def request_context() -> MagicMock:
    context = Mock(spec=RequestContext)
    context.get_user_input.return_value = "test query"
    context.context_id = "test_context"
    context.current_task = Mock(spec=Task)
    context.current_task.id = "test_task"
    context.message = Message(
        role=Role.user,
        task_id="test_task",
        context_id="test_context",
        message_id=str(uuid.uuid4()),
        parts=[Part(root=TextPart(text="Test message"))],
    )
    return context


@pytest.fixture
def event_adapter() -> MagicMock:
    adapter = Mock(spec=A2aEventAdapter)
    adapter.handle_events = AsyncMock()
    return adapter


@pytest.fixture
def state_store() -> MagicMock:
    return Mock(spec=CacheStore)

@pytest.fixture
def get_agent_sync() -> Callable[[A2aExecutionContext], Awaitable[ChatAgent]]:
    async def _get_agent(_: A2aExecutionContext) -> ChatAgent:
        return get_mock_agent()

    return _get_agent

@pytest.fixture
def get_agent_async() -> Callable[[A2aExecutionContext], Awaitable[ChatAgent]]:
    async def _get_agent(_: A2aExecutionContext) -> ChatAgent:
        return get_mock_agent()

    return _get_agent


@pytest.fixture
def executor(get_agent_sync: MagicMock, event_adapter: MagicMock, state_store: MagicMock) -> A2aExecutor:
    return A2aExecutor(get_agent=get_mock_agent, event_adapter=event_adapter, state_store=state_store)


@pytest.mark.asyncio
async def test_executor_initialization(get_agent_sync: MagicMock) -> None:
    """Test executor initialization with different configurations."""
    # Test with minimal configuration
    executor = A2aExecutor(get_agent=get_mock_agent)
    assert isinstance(executor._state_store, InMemoryStore)

    # Test with custom components
    custom_store = Mock(spec=CacheStore)
    custom_adapter = Mock(spec=A2aEventAdapter)
    executor = A2aExecutor(get_agent=get_mock_agent, event_adapter=custom_adapter, state_store=custom_store)
    assert executor._state_store == custom_store
    assert executor._event_adapter == custom_adapter


@pytest.mark.asyncio
async def test_cancellation_token_management(executor: MagicMock, request_context: MagicMock) -> None:
    """Test management of cancellation tokens."""
    # Test ensuring cancellation data
    executor.ensure_cancellation_data(request_context.current_task)
    assert request_context.current_task.id in executor._cancellation_tokens

    # Test clearing cancellation data
    executor.clear_cancellation_data(request_context.current_task)
    assert request_context.current_task.id not in executor._cancellation_tokens


@pytest.mark.asyncio
async def test_cancel_execution(executor: MagicMock, request_context: MagicMock, event_queue: MagicMock) -> None:
    """Test cancellation of execution."""
    executor.ensure_cancellation_data(request_context.current_task)
    await executor.cancel(request_context, event_queue)
    assert executor._cancellation_tokens[request_context.current_task.id]._cancelled


@pytest.mark.asyncio
async def test_get_stateful_agent_sync(executor: MagicMock, request_context: MagicMock, state_store: MagicMock) -> None:
    """Test getting stateful agent with sync agent factory."""
    state_store.get.return_value = {"previous": "state"}
    context = executor.build_context(
        request_context,
        request_context.current_task,
        Mock(spec=TaskUpdater),
        Mock(spec=A2aExternalUserProxyAgent),
        CancellationToken(),
    )

    agent = await executor.get_stateful_agent(context)
    assert isinstance(agent, Mock)
    state_store.get.assert_called_once_with(request_context.current_task.id)
    agent.load_state.assert_called_once_with({"previous": "state"})


@pytest.mark.asyncio
async def test_execute_success(executor: MagicMock, request_context: MagicMock, event_queue: MagicMock) -> None:
    """Test successful execution flow."""
    text = TextMessage(content="Processing...", source="assistant")
    mock_messages: List[TextMessage | TaskResult] = [text, TaskResult(messages=[text])]
    executor._get_agent = lambda _: get_mock_agent(mock_messages)

    await executor.execute(request_context, event_queue)

    # Verify task completion was called
    event_queue.enqueue_event.assert_called()
    executor._event_adapter.handle_events.assert_called()


@pytest.mark.asyncio
async def test_execute_with_user_input(executor: MagicMock, request_context: MagicMock, event_queue: MagicMock) -> None:
    """Test execution with user input request."""
    mock_messages = [
        TextMessage(content="Need input", source="assistant"),
    ]

    async def mock_run_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[TextMessage, None]:
        for message in mock_messages:
            yield message
        raise CancelledError()

    def get_user_cancellation_agent(context: A2aExecutionContext) -> ChatAgent:
        mock_agent = get_mock_agent()
        mock_agent.run_stream = mock_run_stream
        context.user_proxy_agent.is_cancelled_by_me = True
        return mock_agent

    executor._get_agent = get_user_cancellation_agent

    await executor.execute(request_context, event_queue)

    # Verify input required state was set
    assert TaskState.input_required == event_queue.enqueue_event.call_args_list[-1].args[0].status.state


@pytest.mark.asyncio
async def test_execute_with_cancellation(
    executor: MagicMock, request_context: MagicMock, event_queue: MagicMock
) -> None:
    """Test execution with cancellation."""

    mock_messages: List[TextMessage] = []

    async def mock_run_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[TextMessage, None]:
        for message in mock_messages:
            yield message
        raise CancelledError()

    mock_agent = get_mock_agent()
    mock_agent.run_stream = mock_run_stream
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify cancelled state was set
    assert TaskState.canceled == event_queue.enqueue_event.call_args_list[-1].args[0].status.state


@pytest.mark.asyncio
async def test_execute_with_error(executor: MagicMock, request_context: MagicMock, event_queue: MagicMock) -> None:
    """Test execution with error."""

    async def mock_run_stream(*args: Any, **kwargs: Any) -> None:
        raise ValueError("Test error")

    mock_agent = get_mock_agent()
    mock_agent.run_stream = mock_run_stream
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify failed state was set
    assert TaskState.failed == event_queue.enqueue_event.call_args_list[-1].args[0].status.state


@pytest.mark.asyncio
async def test_execute_with_error_while_processing(
    executor: MagicMock, request_context: MagicMock, event_queue: MagicMock
) -> None:
    """Test execution with error."""

    mock_messages = [
        TextMessage(content="Need input", source="assistant"),
    ]

    async def mock_run_stream(*args: Any, **kwargs: Any) -> AsyncGenerator[TextMessage, None]:
        for message in mock_messages:
            yield message
        raise ValueError("Test error")

    mock_agent = get_mock_agent()
    mock_agent.run_stream = mock_run_stream
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify failed state was set
    assert TaskState.failed == event_queue.enqueue_event.call_args_list[-1].args[0].status.state
    assert "Test error" in event_queue.enqueue_event.call_args_list[-1].args[0].status.message.parts[0].root.text


@pytest.mark.asyncio
async def test_state_persistence(
    executor: MagicMock, request_context: MagicMock, event_queue: MagicMock, state_store: MagicMock
) -> None:
    """Test agent state persistence."""
    mock_agent = get_mock_agent([TaskResult(messages=[])])
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify state was saved
    state_store.set.assert_called_once_with(request_context.current_task.id, {"state": "saved"})


@pytest.mark.asyncio
async def test_build_context(executor: MagicMock, request_context: MagicMock) -> None:
    """Test context building."""
    updater = Mock(spec=TaskUpdater)
    user_proxy = Mock(spec=A2aExternalUserProxyAgent)
    token = CancellationToken()

    context = executor.build_context(request_context, request_context.current_task, updater, user_proxy, token)

    assert context.request == request_context
    assert context.task == request_context.current_task
    assert context.updater == updater
    assert context.user_proxy_agent == user_proxy
    assert context.cancellation_token == token
