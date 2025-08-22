from asyncio import CancelledError
from unittest.mock import AsyncMock, Mock, patch

import pytest
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Part, Task, TaskState, TextPart
from autogen_agentchat.base import ChatAgent, TaskResult, Team
from autogen_agentchat.messages import TextMessage, UserInputRequestedEvent
from autogen_core import CacheStore, CancellationToken, InMemoryStore
from autogen_ext.runtimes.a2a._a2a_event_adapter import A2aEventAdapter
from autogen_ext.runtimes.a2a._a2a_executor import A2aExecutor
from autogen_ext.runtimes.a2a._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent


class MockAgent:
    def __init__(self, messages=None):
        self.messages = messages or []
        self.save_state = AsyncMock(return_value={"state": "saved"})
        self.load_state = AsyncMock()

    async def run_stream(self, task, cancellation_token):
        for message in self.messages:
            yield message


@pytest.fixture
def event_queue():
    queue = Mock(spec=EventQueue)
    queue.enqueue_event = AsyncMock()
    return queue


@pytest.fixture
def request_context():
    context = Mock(spec=RequestContext)
    context.get_user_input.return_value = "test query"
    context.context_id = "test_context"
    context.current_task = Mock(spec=Task)
    context.current_task.id = "test_task"
    context.message = Message(text="test message")
    return context


@pytest.fixture
def event_adapter():
    adapter = Mock(spec=A2aEventAdapter)
    adapter.handle_events = AsyncMock()
    return adapter


@pytest.fixture
def state_store():
    return Mock(spec=CacheStore)


@pytest.fixture
def get_agent_sync():
    def _get_agent(_):
        return MockAgent()

    return _get_agent


@pytest.fixture
def get_agent_async():
    async def _get_agent(_):
        return MockAgent()

    return _get_agent


@pytest.fixture
def executor(get_agent_sync, event_adapter, state_store):
    return A2aExecutor(get_agent=get_agent_sync, event_adapter=event_adapter, state_store=state_store)


@pytest.mark.asyncio
async def test_executor_initialization(get_agent_sync):
    """Test executor initialization with different configurations."""
    # Test with minimal configuration
    executor = A2aExecutor(get_agent=get_agent_sync)
    assert isinstance(executor._state_store, InMemoryStore)

    # Test with custom components
    custom_store = Mock(spec=CacheStore)
    custom_adapter = Mock(spec=A2aEventAdapter)
    executor = A2aExecutor(get_agent=get_agent_sync, event_adapter=custom_adapter, state_store=custom_store)
    assert executor._state_store == custom_store
    assert executor._event_adapter == custom_adapter


@pytest.mark.asyncio
async def test_cancellation_token_management(executor, request_context):
    """Test management of cancellation tokens."""
    # Test ensuring cancellation data
    executor.ensure_cancellation_data(request_context.current_task)
    assert request_context.current_task.id in executor._cancellation_tokens

    # Test clearing cancellation data
    executor.clear_cancellation_data(request_context.current_task)
    assert request_context.current_task.id not in executor._cancellation_tokens


@pytest.mark.asyncio
async def test_cancel_execution(executor, request_context, event_queue):
    """Test cancellation of execution."""
    executor.ensure_cancellation_data(request_context.current_task)
    await executor.cancel(request_context, event_queue)
    assert executor._cancellation_tokens[request_context.current_task.id].cancelled


@pytest.mark.asyncio
async def test_get_stateful_agent_sync(executor, request_context, state_store):
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
    assert isinstance(agent, MockAgent)
    state_store.get.assert_called_once_with(request_context.current_task.id)
    agent.load_state.assert_called_once_with({"previous": "state"})


@pytest.mark.asyncio
async def test_get_stateful_agent_async(get_agent_async, event_adapter, state_store):
    """Test getting stateful agent with async agent factory."""
    executor = A2aExecutor(get_agent=get_agent_async, event_adapter=event_adapter, state_store=state_store)
    context = executor.build_context(
        Mock(spec=RequestContext),
        Mock(spec=Task, id="test_task"),
        Mock(spec=TaskUpdater),
        Mock(spec=A2aExternalUserProxyAgent),
        CancellationToken(),
    )

    agent = await executor.get_stateful_agent(context)
    assert isinstance(agent, MockAgent)


@pytest.mark.asyncio
async def test_execute_success(executor, request_context, event_queue):
    """Test successful execution flow."""
    mock_messages = [TextMessage(content="Processing...", source="assistant"), TaskResult(success=True)]
    executor._get_agent = lambda _: MockAgent(mock_messages)

    await executor.execute(request_context, event_queue)

    # Verify task completion was called
    event_queue.enqueue_event.assert_called()
    executor._event_adapter.handle_events.assert_called()


@pytest.mark.asyncio
async def test_execute_with_user_input(executor, request_context, event_queue):
    """Test execution with user input request."""
    mock_messages = [
        TextMessage(content="Need input", source="assistant"),
        UserInputRequestedEvent(prompt="Please provide input"),
    ]
    executor._get_agent = lambda _: MockAgent(mock_messages)

    await executor.execute(request_context, event_queue)

    # Verify input required state was set
    assert any(
        call.kwargs.get("state") == TaskState.input_required for call in event_queue.enqueue_event.call_args_list
    )


@pytest.mark.asyncio
async def test_execute_with_cancellation(executor, request_context, event_queue):
    """Test execution with cancellation."""

    async def mock_run_stream(*args, **kwargs):
        raise CancelledError()

    mock_agent = MockAgent()
    mock_agent.run_stream = mock_run_stream
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify cancelled state was set
    assert any(call.kwargs.get("state") == TaskState.canceled for call in event_queue.enqueue_event.call_args_list)


@pytest.mark.asyncio
async def test_execute_with_error(executor, request_context, event_queue):
    """Test execution with error."""

    async def mock_run_stream(*args, **kwargs):
        raise ValueError("Test error")

    mock_agent = MockAgent()
    mock_agent.run_stream = mock_run_stream
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify failed state was set
    assert any(call.kwargs.get("state") == TaskState.failed for call in event_queue.enqueue_event.call_args_list)


@pytest.mark.asyncio
async def test_state_persistence(executor, request_context, event_queue, state_store):
    """Test agent state persistence."""
    mock_agent = MockAgent([TaskResult(success=True)])
    executor._get_agent = lambda _: mock_agent

    await executor.execute(request_context, event_queue)

    # Verify state was saved
    state_store.set.assert_called_once_with(request_context.current_task.id, {"state": "saved"})


@pytest.mark.asyncio
async def test_build_context(executor, request_context):
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
