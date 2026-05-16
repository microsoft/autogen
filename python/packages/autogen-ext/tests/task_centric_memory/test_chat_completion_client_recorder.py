import json
from pathlib import Path

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


@pytest.mark.asyncio
async def test_record(tmp_path: Path) -> None:
    """Test that in record mode, create() records the interaction and writes to disk on finalize()."""
    session_file_path = str(tmp_path / "session_1.json")
    logger = PageLogger(config={"level": "DEBUG", "path": str(tmp_path / "logs")})
    logger.enter_function()
    logger.info("Page log UTF-8 text: café 測試")

    mock_client = ReplayChatCompletionClient(
        [
            "Response to message 1 with UTF-8 text: café 測試",
        ]
    )
    recorder = ChatCompletionClientRecorder(
        mock_client, mode="record", session_file_path=session_file_path, logger=logger
    )

    messages = [UserMessage(content="Message 1 with UTF-8 text: naïve 測試", source="User")]
    response = await recorder.create(messages)
    assert isinstance(response, CreateResult)
    assert response.content == "Response to message 1 with UTF-8 text: café 測試"

    recorder.finalize()
    logger.leave_function()
    logger.finalize()
    records = json.loads(Path(session_file_path).read_text(encoding="utf-8"))
    assert records[0]["response"]["content"] == "Response to message 1 with UTF-8 text: café 測試"
    assert "café 測試" in (tmp_path / "logs" / "1.html").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_replay(tmp_path: Path) -> None:
    """
    Test that in replay mode, create() replays the recorded response if the messages match,
    and raises an error if they do not or if records run out.
    """
    session_file_path = str(tmp_path / "session_1.json")
    record_logger = PageLogger(config={"level": "DEBUG", "path": str(tmp_path / "record_logs")})
    record_logger.enter_function()
    recorder = ChatCompletionClientRecorder(
        ReplayChatCompletionClient(["Response to message 1 with UTF-8 text: café 測試"]),
        mode="record",
        session_file_path=session_file_path,
        logger=record_logger,
    )
    messages = [UserMessage(content="Message 1 with UTF-8 text: naïve 測試", source="User")]
    await recorder.create(messages)
    recorder.finalize()
    record_logger.leave_function()
    record_logger.finalize()

    logger = PageLogger(config={"level": "DEBUG", "path": str(tmp_path / "replay_logs")})
    logger.enter_function()
    mock_client = ReplayChatCompletionClient(
        [
            "Response that should not be returned",
        ]
    )
    recorder = ChatCompletionClientRecorder(
        mock_client, mode="replay", session_file_path=session_file_path, logger=logger
    )

    response = await recorder.create(messages)
    assert isinstance(response, CreateResult)
    assert response.content == "Response to message 1 with UTF-8 text: café 測試"

    recorder.finalize()
    logger.leave_function()
    logger.finalize()
