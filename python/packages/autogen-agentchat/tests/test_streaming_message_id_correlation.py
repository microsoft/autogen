from typing import List, Optional

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import FunctionCall
from autogen_core.models import CreateResult, ModelFamily, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient


async def _echo_function(input: str) -> str:
    return input


@pytest.mark.asyncio
async def test_streaming_message_id_correlation() -> None:
    """Test that streaming chunks have full_message_id that matches final message ID."""
    mock_client = ReplayChatCompletionClient(
        [
            "Response to message",
        ]
    )
    agent = AssistantAgent(
        "test_agent",
        model_client=mock_client,
        model_client_stream=True,
    )

    # Track all chunks and the final message
    chunks: List[ModelClientStreamingChunkEvent] = []
    final_message: Optional[TextMessage] = None

    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            assert len(message.messages) == 2
            assert isinstance(message.messages[0], TextMessage)
            assert isinstance(message.messages[1], TextMessage)
            final_message = message.messages[1]
        elif isinstance(message, ModelClientStreamingChunkEvent):
            chunks.append(message)

    # Verify we got chunks and a final message
    assert len(chunks) > 0
    assert final_message is not None

    # Every chunk should have the same full_message_id as the final message's id
    for chunk in chunks:
        assert chunk.full_message_id == final_message.id

    # Test the reflect_on_tool_use streaming case
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                content=[
                    FunctionCall(id="1", name="_echo_function", arguments=r'{"input": "task"}'),
                ],
                finish_reason="function_calls",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            "Example reflection response",
        ],
        model_info={
            "function_calling": True,
            "vision": False,
            "json_output": False,
            "family": ModelFamily.GPT_4,
            "structured_output": False,
        },
    )

    agent = AssistantAgent(
        "test_agent",
        model_client=mock_client,
        model_client_stream=True,
        reflect_on_tool_use=True,
        tools=[_echo_function],
    )

    # Track reflection chunks and final message
    reflection_chunks: List[ModelClientStreamingChunkEvent] = []
    final_reflection_message: Optional[TextMessage] = None

    async for message in agent.run_stream(task="task"):
        if isinstance(message, TaskResult):
            # The last message should be the reflection result
            if isinstance(message.messages[-1], TextMessage):
                final_reflection_message = message.messages[-1]
        elif isinstance(message, ModelClientStreamingChunkEvent):
            reflection_chunks.append(message)

    # Verify we got reflection chunks and a final message
    assert len(reflection_chunks) > 0
    assert final_reflection_message is not None

    # Every reflection chunk should have the same full_message_id as the final message's id
    for chunk in reflection_chunks:
        assert chunk.full_message_id == final_reflection_message.id  # type: ignore
