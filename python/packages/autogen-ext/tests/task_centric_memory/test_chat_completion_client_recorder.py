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


@pytest.mark.asyncio
async def test_record_and_replay_with_utf8_characters() -> None:
    """Test that session files containing raw UTF-8 bytes round-trip correctly.

    On Windows with a non-UTF-8 default encoding (e.g. cp936/gbk), opening
    a text file without ``encoding="utf-8"`` can corrupt data or raise
    ``UnicodeDecodeError``. We guard this by explicitly using UTF-8 when
    reading and writing the session file.
    """
    import json
    import os
    import tempfile

    logger = PageLogger(config={"level": "DEBUG", "path": "./logs"})
    logger.enter_function()

    # Create a session file that contains *raw* UTF-8 bytes (not \uXXXX escapes).
    # This simulates a file produced on a Linux/macOS machine or by a tool
    # that writes JSON with ensure_ascii=False.
    session_data = [
        {
            "mode": "create",
            "messages": [{"content": "Bonjour 你好", "source": "User", "type": "UserMessage"}],
            "response": {
                "content": "Réponse en français: café 你好世界",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 2, "completion_tokens": 5},
                "cached": True,
                "logprobs": None,
                "thought": None,
            },
            "stream": [],
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
        session_file = f.name

    # Replay mode: must be able to load the raw-UTF-8 session file.
    mock_client = ReplayChatCompletionClient(["ignored"])
    recorder = ChatCompletionClientRecorder(
        mock_client, mode="replay", session_file_path=session_file, logger=logger
    )
    messages = [UserMessage(content="Bonjour 你好", source="User")]
    response = await recorder.create(messages)
    assert response.content == "Réponse en français: café 你好世界"
    recorder.finalize()

    # Record mode: finalize() must also succeed with UTF-8 encoding.
    # We test this by recording new non-ASCII content and reloading it.
    mock_client2 = ReplayChatCompletionClient(["新回复"])
    recorder2 = ChatCompletionClientRecorder(
        mock_client2, mode="record", session_file_path=session_file, logger=logger
    )
    messages2 = [UserMessage(content="新消息", source="User")]
    response2 = await recorder2.create(messages2)
    assert response2.content == "新回复"
    recorder2.finalize()

    # Verify the recorded file can be replayed.
    recorder3 = ChatCompletionClientRecorder(
        mock_client2, mode="replay", session_file_path=session_file, logger=logger
    )
    response3 = await recorder3.create(messages2)
    assert response3.content == "新回复"
    recorder3.finalize()

    os.unlink(session_file)
    logger.leave_function()


if __name__ == "__main__":
    asyncio.run(test_record())
    asyncio.run(test_replay())
    asyncio.run(test_record_and_replay_with_utf8_characters())
