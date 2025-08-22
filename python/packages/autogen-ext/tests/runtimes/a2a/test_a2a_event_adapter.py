import base64
import io
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from a2a.types import Artifact, DataPart, Part, TaskArtifactUpdateEvent, TaskState, TextPart
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, MultiModalMessage, StructuredMessage, TextMessage
from autogen_core import CancellationToken, Image
from autogen_ext.runtimes.a2a._a2a_event_adapter import BaseA2aEventAdapter
from autogen_ext.runtimes.a2a._a2a_execution_context import A2aExecutionContext
from PIL import Image as PILImage
from pydantic import BaseModel  # Changed from pydantic.v1 to pydantic


def to_base64() -> str:
    img = PILImage.new("RGB", (100, 100), color="red")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    content = buffered.getvalue()
    return base64.b64encode(content).decode("utf-8")


b64_img = to_base64()
img_data_uri = f"data:image/png;base64,{b64_img}"
img_object = Image.from_uri(img_data_uri)


@pytest.fixture
def context() -> A2aExecutionContext:
    mock_updater = AsyncMock()
    mock_updater.task_id = "test_task"
    mock_updater.context_id = "test_context"
    mock_updater.event_queue = AsyncMock()
    mock_updater.event_queue.enqueue_event = AsyncMock()
    mock_updater.update_status = AsyncMock()
    mock_updater.new_agent_message = Mock(return_value="test_message")

    mock_user_proxy = Mock()
    mock_user_proxy.name = "user_proxy"

    return A2aExecutionContext(
        updater=mock_updater,
        user_proxy_agent=mock_user_proxy,
        cancellation_token=CancellationToken(),
        task=Mock(),
        request=Mock(),
    )


@pytest.mark.asyncio
async def test_handle_text_message(context: AsyncMock) -> None:
    adapter = BaseA2aEventAdapter()
    message = TextMessage(content="Hello, world!", source="assistant")

    await adapter.handle_events(message, context)

    context.updater.new_agent_message.assert_called_once_with(
        [Part(root=TextPart(text="Hello, world!"))], metadata=None
    )
    context.updater.update_status.assert_called_once_with(state=TaskState.working, message="test_message")


@pytest.mark.asyncio
async def test_ignore_user_proxy_message(context: AsyncMock) -> None:
    adapter = BaseA2aEventAdapter()
    message = TextMessage(content="User input", source="user_proxy")

    await adapter.handle_events(message, context)

    context.updater.update_status.assert_not_called()


@pytest.mark.asyncio
async def test_handle_multimodal_message(context: AsyncMock) -> None:
    adapter = BaseA2aEventAdapter()
    image = img_object
    message = MultiModalMessage(content=["Image description:", image], source="assistant")

    await adapter.handle_events(message, context)

    context.updater.new_agent_message.assert_called_once()
    assert len(context.updater.new_agent_message.call_args[1]["parts"]) == 2


class Data(BaseModel):
    key: str
    model_config = {"extra": "forbid"}


@pytest.mark.asyncio
async def test_handle_structured_message(context: AsyncMock) -> None:
    adapter = BaseA2aEventAdapter()
    data = Data(key="value")
    message = StructuredMessage[Data](content=data, source="assistant", format_string="{key}")

    await adapter.handle_events(message, context)

    context.updater.new_agent_message.assert_called_once_with(
        parts=[Part(root=DataPart(data=data.model_dump()))], metadata={}
    )


@pytest.mark.asyncio
async def test_handle_streaming_chunk_event(context: AsyncMock) -> None:
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
async def test_streaming_chunk_closure(context: AsyncMock) -> None:
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
