import pytest
from unittest.mock import Mock, AsyncMock
from a2a.server.agent_execution import RequestContext
from a2a.server.tasks import TaskUpdater
from a2a.types import Task, TaskState
from autogen_core import CancellationToken

from autogen_ext.runtimes.a2a._a2a_execution_context import A2aExecutionContext
from autogen_ext.runtimes.a2a._a2a_external_user_proxy_agent import A2aExternalUserProxyAgent

@pytest.fixture
def task():
    return Mock(spec=Task)

@pytest.fixture
def updater():
    mock_updater = Mock(spec=TaskUpdater)
    mock_updater.update_status = AsyncMock()
    return mock_updater

@pytest.fixture
def user_proxy_agent():
    mock_agent = Mock(spec=A2aExternalUserProxyAgent)
    mock_agent.name = "user_proxy"
    mock_agent.request_input = AsyncMock()
    return mock_agent

@pytest.fixture
def request_context():
    mock_request = Mock(spec=RequestContext)
    mock_request.context_id = "test_context"
    mock_request.metadata = {"key": "value"}
    mock_request.params = {"param": "value"}
    return mock_request

@pytest.fixture
def cancellation_token():
    return CancellationToken()

@pytest.fixture
def execution_context(task, updater, user_proxy_agent, request_context, cancellation_token):
    return A2aExecutionContext(
        request=request_context,
        task=task,
        updater=updater,
        user_proxy_agent=user_proxy_agent,
        cancellation_token=cancellation_token
    )

def test_initialization(execution_context, task, updater, user_proxy_agent, request_context, cancellation_token):
    """Test that the execution context is properly initialized with all components."""
    assert execution_context.task == task
    assert execution_context.updater == updater
    assert execution_context.user_proxy_agent == user_proxy_agent
    assert execution_context.request == request_context
    assert execution_context.cancellation_token == cancellation_token
    assert execution_context.streaming_chunks_id is None

def test_streaming_chunks_id_property(execution_context):
    """Test setting and getting streaming_chunks_id."""
    # Test initial state
    assert execution_context.streaming_chunks_id is None
    
    # Test setting new value
    execution_context.streaming_chunks_id = "test_stream_123"
    assert execution_context.streaming_chunks_id == "test_stream_123"
    
    # Test setting back to None
    execution_context.streaming_chunks_id = None
    assert execution_context.streaming_chunks_id is None

@pytest.mark.asyncio
async def test_updater_property(execution_context, updater):
    """Test the updater property and its methods."""
    assert execution_context.updater == updater
    
    # Test that updater methods are accessible and working
    await execution_context.updater.update_status(state=TaskState.working)
    updater.update_status.assert_called_once_with(state=TaskState.working)

def test_user_proxy_agent_property(execution_context, user_proxy_agent):
    """Test the user_proxy_agent property and its attributes."""
    assert execution_context.user_proxy_agent == user_proxy_agent
    assert execution_context.user_proxy_agent.name == "user_proxy"

@pytest.mark.asyncio
async def test_user_proxy_agent_request_input(execution_context, user_proxy_agent):
    """Test the user_proxy_agent's request_input method."""
    user_proxy_agent.request_input.return_value = "user response"
    
    response = await execution_context.user_proxy_agent.request_input("Please provide input")
    
    assert response == "user response"
    user_proxy_agent.request_input.assert_called_once_with("Please provide input")

def test_request_property(execution_context, request_context):
    """Test the request property and its attributes."""
    assert execution_context.request == request_context
    assert execution_context.request.context_id == "test_context"
    assert execution_context.request.metadata == {"key": "value"}
    assert execution_context.request.params == {"param": "value"}

def test_cancellation_token_property(execution_context, cancellation_token):
    """Test the cancellation_token property and its functionality."""
    assert execution_context.cancellation_token == cancellation_token
    assert not execution_context.cancellation_token.cancelled
    
    # Test cancellation
    execution_context.cancellation_token.cancel()
    assert execution_context.cancellation_token.cancelled

def test_task_property(execution_context, task):
    """Test the task property and its attributes."""
    assert execution_context.task == task

def test_cancellation_token_callback(execution_context):
    """Test registering and triggering cancellation callbacks."""
    callback_called = False
    
    def on_cancel():
        nonlocal callback_called
        callback_called = True
    
    execution_context.cancellation_token.register(on_cancel)
    assert not callback_called
    
    execution_context.cancellation_token.cancel()
    assert callback_called

@pytest.mark.asyncio
async def test_context_with_cancellation(execution_context):
    """Test context behavior when cancellation occurs during operation."""
    async def async_operation():
        if execution_context.cancellation_token.cancelled:
            return "cancelled"
        return "completed"
    
    # Test without cancellation
    result = await async_operation()
    assert result == "completed"
    
    # Test with cancellation
    execution_context.cancellation_token.cancel()
    result = await async_operation()
    assert result == "cancelled"

def test_immutable_properties(execution_context):
    """Test that properties cannot be modified after initialization."""
    with pytest.raises(AttributeError):
        execution_context.task = Mock()
    
    with pytest.raises(AttributeError):
        execution_context.updater = Mock()
    
    with pytest.raises(AttributeError):
        execution_context.user_proxy_agent = Mock()
    
    with pytest.raises(AttributeError):
        execution_context.request = Mock()
    
    with pytest.raises(AttributeError):
        execution_context.cancellation_token = CancellationToken()
