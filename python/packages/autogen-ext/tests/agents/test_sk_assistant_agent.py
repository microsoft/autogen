from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock


import pytest
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    ChatMessage,
    HandoffMessage,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallSummaryMessage,
)
from autogen_core import CancellationToken, Image
from autogen_ext.agents.semantic_kernel._sk_assistant_agent import SKAssistantAgent
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.exceptions import KernelServiceNotFoundError
from semantic_kernel.kernel import Kernel


@pytest.fixture
def mock_kernel() -> MagicMock:
    """
    Provide a mock Kernel that returns a mock ChatCompletionClientBase
    when get_service is called.
    """
    kernel = MagicMock(spec=Kernel)
    kernel.get_service = MagicMock()
    kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value=None)
    return kernel


@pytest.fixture
def mock_chat_service() -> MagicMock:
    """
    Provide a mock ChatCompletionClientBase for returning from the kernel.
    """

    class AsyncIteratorMock:
        def __init__(self, items: list[list[ChatMessageContent]]) -> None:
            self.items = items

        def __aiter__(self) -> AsyncIterator[list[ChatMessageContent]]:
            return self

        async def __anext__(self) -> list[ChatMessageContent]:
            try:
                return self.items.pop(0)
            except IndexError as e:
                raise StopAsyncIteration from e

    service = MagicMock(spec=ChatCompletionClientBase)
    service.get_chat_message_contents = AsyncMock(return_value=[])
    mock_stream_responses = [
        [ChatMessageContent(role=AuthorRole.ASSISTANT, content="Chunk1 ")],
        [ChatMessageContent(role=AuthorRole.ASSISTANT, content="Chunk2")],
    ]
    service.get_streaming_chat_message_contents = MagicMock(return_value=AsyncIteratorMock(mock_stream_responses))
    service.instantiate_prompt_execution_settings = MagicMock(return_value=PromptExecutionSettings())
    service.ai_model_id = "mock-model-id"
    return service


@pytest.mark.asyncio
async def test_on_messages_text_message(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages with a simple TextMessage.
    """
    # Arrange
    mock_kernel.get_service.return_value = mock_chat_service
    # Mock the response from get_chat_message_contents
    mock_chat_service.get_chat_message_contents.return_value = [
        ChatMessageContent(role=AuthorRole.ASSISTANT, content="Mocked assistant reply")
    ]

    agent = SKAssistantAgent(
        name="TestAgent",
        description="Testing SKAssistantAgent",
        kernel=mock_kernel,
        instructions="System instructions.",
    )

    messages = [
        TextMessage(content="Hello world!", source="user"),
    ]

    # Act
    response = await agent.on_messages(messages, CancellationToken())

    # Assert
    assert response.chat_message.content == "Mocked assistant reply"
    assert response.chat_message.source == "TestAgent"
    assert len(agent._chat_history.messages) == 3  # type: ignore
    mock_chat_service.get_chat_message_contents.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_messages_multi_modal(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages with a MultiModalMessage that has both text and an image.
    """
    # Arrange
    mock_kernel.get_service.return_value = mock_chat_service
    mock_chat_service.get_chat_message_contents.return_value = [
        ChatMessageContent(role=AuthorRole.ASSISTANT, content="Image accepted.")
    ]

    agent = SKAssistantAgent(
        name="TestAgent",
        description="Testing SKAssistantAgent",
        kernel=mock_kernel,
    )

    single_byte_image = Image.from_base64(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgAAIAAAUAAen6L8YAAAAASUVORK5CYII="
    )
    messages = [MultiModalMessage(content=["Here is an image", single_byte_image], source="user")]

    # Act
    response = await agent.on_messages(messages, CancellationToken())

    # Assert
    assert response.chat_message.content == "Image accepted."
    assert response.chat_message.source == "TestAgent"
    # 2 messages in chat_history: user + assistant
    assert len(agent._chat_history.messages) == 2  # type: ignore
    mock_chat_service.get_chat_message_contents.assert_awaited_once()  # type: ignore


@pytest.mark.asyncio
async def test_on_messages_stop_message(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages with a StopMessage.
    """
    mock_kernel.get_service.return_value = mock_chat_service
    mock_chat_service.get_chat_message_contents.return_value = [
        ChatMessageContent(role=AuthorRole.ASSISTANT, content="Stopping now.")
    ]
    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel)

    messages = [
        StopMessage(content="Please stop.", source="user"),
    ]

    response = await agent.on_messages(messages, CancellationToken())
    assert response.chat_message.content == "Stopping now."
    assert len(agent._chat_history.messages) == 2  # type: ignore


@pytest.mark.asyncio
async def test_on_messages_tool_call_summary(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages with a ToolCallSummaryMessage.
    """
    mock_kernel.get_service.return_value = mock_chat_service
    mock_chat_service.get_chat_message_contents.return_value = [
        ChatMessageContent(role=AuthorRole.ASSISTANT, content="Tool call summary acknowledged.")
    ]
    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel)

    messages = [
        ToolCallSummaryMessage(content="Summary of tool call", source="user"),
    ]

    response = await agent.on_messages(messages, CancellationToken())
    assert response.chat_message.content == "Tool call summary acknowledged."
    assert len(agent._chat_history.messages) == 2  # type: ignore


@pytest.mark.asyncio
async def test_on_messages_handoff_message(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages with a HandoffMessage.
    """
    mock_kernel.get_service.return_value = mock_chat_service
    mock_chat_service.get_chat_message_contents.return_value = [
        ChatMessageContent(role=AuthorRole.ASSISTANT, content="Handoff message received.")
    ]
    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel)

    messages = [
        HandoffMessage(target="AnotherAgent", content="Please handle this conversation.", source="user", context=[]),
    ]

    response = await agent.on_messages(messages, CancellationToken())
    assert response.chat_message.content == "Handoff message received."
    assert len(agent._chat_history.messages) == 2  # type: ignore


@pytest.mark.asyncio
async def test_on_messages_no_service_found(mock_kernel: MagicMock) -> None:
    """
    Test that a KernelServiceNotFoundError is raised if there's no chat service with the given service_id.
    """
    mock_kernel.get_service.return_value = None
    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel, service_id="not-found")

    with pytest.raises(KernelServiceNotFoundError):
        await agent.on_messages([TextMessage(content="test", source="user")], CancellationToken())


@pytest.mark.asyncio
async def test_on_reset_clears_history(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_reset to ensure conversation history is cleared.
    """
    mock_kernel.get_service.return_value = mock_chat_service

    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel)
    # Add some messages
    await agent.on_messages([TextMessage(content="Hello", source="user")], CancellationToken())
    assert len(agent._chat_history.messages) > 0  # type: ignore

    # Reset
    await agent.on_reset(CancellationToken())
    assert len(agent._chat_history.messages) == 0  # type: ignore


@pytest.mark.asyncio
async def test_on_messages_stream(mock_kernel: MagicMock, mock_chat_service: MagicMock) -> None:
    """
    Test on_messages_stream yields partial text and then a final response.
    """

    # Simulate streaming two chunks back to back
    # The get_streaming_chat_message_contents async generator yields lists of ChatMessageContent
    async def mock_stream(*args: Any, **kwargs: Any) -> AsyncIterator[list[ChatMessageContent]]:
        yield [ChatMessageContent(role=AuthorRole.ASSISTANT, content="Chunk1 ")]
        yield [ChatMessageContent(role=AuthorRole.ASSISTANT, content="Chunk2")]

    mock_chat_service.get_streaming_chat_message_contents.side_effect = mock_stream

    mock_kernel.get_service.return_value = mock_chat_service

    agent = SKAssistantAgent("TestAgent", "desc", mock_kernel)

    messages = [TextMessage(content="Hello streaming!", source="user")]
    results: list[ChatMessage | Response] = []
    async for item in agent.on_messages_stream(messages, CancellationToken()):
        results.append(item)

    # The stream should yield 2 partial TextMessages, then 1 final Response
    assert len(results) == 1
    assert isinstance(results[0], Response)
    assert results[0].chat_message.content == "Chunk1 Chunk2"
    # chat_history should now have user + assistant
    assert len(agent._chat_history.messages) == 2  # type: ignore
    assert mock_chat_service.get_streaming_chat_message_contents.call_count == 1  # type: ignore
