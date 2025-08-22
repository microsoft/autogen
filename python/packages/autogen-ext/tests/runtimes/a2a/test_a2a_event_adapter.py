import json
import pytest
from unittest.mock import AsyncMock, Mock

from autogen_agentchat.messages import TextMessage, MultiModalMessage, StructuredMessage, ModelClientStreamingChunkEvent
from autogen_core import Image
from a2a.types import TaskState, Part, TextPart, FilePart, DataPart, FileWithBytes, TaskArtifactUpdateEvent, Artifact

from autogen_ext.runtimes.a2a._a2a_event_adapter import BaseA2aEventAdapter
from autogen_ext.runtimes.a2a._a2a_execution_context import A2aExecutionContext

@pytest.fixture
def context():
    mock_updater = Mock()
    mock_updater.task_id = "test_task"
    mock_updater.context_id = "test_context"
    mock_updater.event_queue = Mock()
    mock_updater.event_queue.enqueue_event = AsyncMock()
    mock_updater.update_status = AsyncMock()
    mock_updater.new_agent_message = Mock(return_value="test_message")
    
    mock_user_proxy = Mock()
    mock_user_proxy.name = "user_proxy"
    
    return A2aExecutionContext(
        updater=mock_updater,
        user_proxy_agent=mock_user_proxy
    )

@pytest.mark.asyncio
async def test_handle_text_message(context):
    adapter = BaseA2aEventAdapter()
    message = TextMessage(content="Hello, world!", source="assistant")
    
    await adapter.handle_events(message, context)
    
    context.updater.new_agent_message.assert_called_once_with(
        [Part(root=TextPart(text="Hello, world!"))],
        metadata=None
    )
    context.updater.update_status.assert_called_once_with(
        state=TaskState.working,
        message="test_message"
    )

@pytest.mark.asyncio
async def test_ignore_user_proxy_message(context):
    adapter = BaseA2aEventAdapter()
    message = TextMessage(content="User input", source="user_proxy")
    
    await adapter.handle_events(message, context)
    
    context.updater.update_status.assert_not_called()

@pytest.mark.asyncio
async def test_handle_multimodal_message(context):
    adapter = BaseA2aEventAdapter()
    image = Image(data=b"fake_image_data")
    message = MultiModalMessage(content=["Image description:", image], source="assistant")
    
    await adapter.handle_events(message, context)
    
    expected_parts = [
        Part(root=TextPart(text="Image description:")),
        Part(root=FilePart(file=FileWithBytes(bytes=image.to_base64())))
    ]
    context.updater.new_agent_message.assert_called_once()
    assert len(context.updater.new_agent_message.call_args[1]["parts"]) == 2

@pytest.mark.asyncio
async def test_handle_structured_message(context):
    adapter = BaseA2aEventAdapter()
    data = {"key": "value"}
    message = StructuredMessage(content=json.dumps(data), source="assistant")
    
    await adapter.handle_events(message, context)
    
    context.updater.new_agent_message.assert_called_once_with(
        parts=[Part(root=DataPart(data=data))],
        metadata=None
    )

@pytest.mark.asyncio
async def test_handle_streaming_chunk_event(context):
    adapter = BaseA2aEventAdapter()
    message = ModelClientStreamingChunkEvent(content="chunk", source="assistant")
    
    await adapter.handle_events(message, context)
    
    context.updater.event_queue.enqueue_event.assert_called_once()
    call_args = context.updater.event_queue.enqueue_event.call_args[0][0]
    assert isinstance(call_args, TaskArtifactUpdateEvent)
    assert call_args.task_id == "test_task"
    assert call_args.context_id == "test_context"
    assert call_args.append is True
    assert isinstance(call_args.artifact, Artifact)
    assert len(call_args.artifact.parts) == 1
    assert call_args.artifact.parts[0].root == TextPart(text="chunk")

@pytest.mark.asyncio
async def test_streaming_chunk_closure(context):
    adapter = BaseA2aEventAdapter()
    # First send a streaming chunk
    chunk_message = ModelClientStreamingChunkEvent(content="chunk", source="assistant")
    await adapter.handle_events(chunk_message, context)
    
    # Then send a non-streaming message to close the stream
    text_message = TextMessage(content="Hello", source="assistant")
    await adapter.handle_events(text_message, context)
    
    # Should have 2 calls - one for chunk, one for closure
    assert context.updater.event_queue.enqueue_event.call_count == 2
    
    # Verify the closure event
    closure_call = context.updater.event_queue.enqueue_event.call_args_list[1]
    closure_event = closure_call[0][0]
    assert closure_event.last_chunk is True
    assert closure_event.append is True
    assert len(closure_event.artifact.parts) == 0

@pytest.mark.asyncio
async def test_multimodal_message_invalid_content():
    adapter = BaseA2aEventAdapter()
    message = MultiModalMessage(content=[42], source="assistant")  # Invalid content type
    
    with pytest.raises(AssertionError, match="Multimodal message content must be an Image or a string."):
        await adapter.handle_events(message, Mock())
