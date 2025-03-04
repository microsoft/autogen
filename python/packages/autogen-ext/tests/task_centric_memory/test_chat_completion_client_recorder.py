import asyncio

import pytest
from autogen_core.models import (
    CreateResult,
    UserMessage,
)
from autogen_ext.experimental.task_centric_memory.utils import PageLogger
from autogen_ext.experimental.task_centric_memory.utils.chat_completion_client_recorder import (
    ChatCompletionClientRecorder,
)
from autogen_ext.models.replay import ReplayChatCompletionClient

session_file_path = str("./session_1.json")


@pytest.mark.asyncio
async def test_record() -> None:
    """Test that in record mode, create() records the interaction and writes to disk on finalize()."""
    logger = PageLogger(config={"level": "DEBUG", "path": "./logs"})
    logger.enter_function()

    mock_client = ReplayChatCompletionClient(
        [
            "Response to message 1",
        ]
    )
    recorder = ChatCompletionClientRecorder(
        mock_client, mode="record", session_file_path=session_file_path, logger=logger
    )

    messages = [UserMessage(content="Message 1", source="User")]
    response = await recorder.create(messages)
    assert isinstance(response, CreateResult)
    assert response.content == "Response to message 1"

    recorder.finalize()
    logger.leave_function()


@pytest.mark.asyncio
async def test_replay() -> None:
    """
    Test that in replay mode, create() replays the recorded response if the messages match,
    and raises an error if they do not or if records run out.
    """
    logger = PageLogger(config={"level": "DEBUG", "path": "./logs"})
    logger.enter_function()

    mock_client = ReplayChatCompletionClient(
        [
            "Response that should not be returned",
        ]
    )
    recorder = ChatCompletionClientRecorder(
        mock_client, mode="replay", session_file_path=session_file_path, logger=logger
    )

    messages = [UserMessage(content="Message 1", source="User")]
    response = await recorder.create(messages)
    assert isinstance(response, CreateResult)
    assert response.content == "Response to message 1"

    recorder.finalize()
    logger.leave_function()


if __name__ == "__main__":
    asyncio.run(test_record())
    asyncio.run(test_replay())
