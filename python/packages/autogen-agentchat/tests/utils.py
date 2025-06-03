import json
import logging
import sys
from datetime import datetime
from typing import Sequence

from autogen_agentchat.base._task import TaskResult
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, BaseTextChatMessage
from pydantic import BaseModel


class FileLogHandler(logging.Handler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, BaseModel):
            record.msg = json.dumps(
                {
                    "timestamp": ts,
                    "message": record.msg.model_dump_json(indent=2),
                    "type": record.msg.__class__.__name__,
                },
            )
        self.file_handler.emit(record)


class ConsoleLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, BaseModel):
            record.msg = json.dumps(
                {
                    "timestamp": ts,
                    "message": record.msg.model_dump_json(indent=2),
                    "type": record.msg.__class__.__name__,
                },
            )
        sys.stdout.write(f"{record.msg}\n")


def compare_messages(
    msg1: BaseAgentEvent | BaseChatMessage | BaseTextChatMessage,
    msg2: BaseAgentEvent | BaseChatMessage | BaseTextChatMessage,
) -> bool:
    if isinstance(msg1, BaseTextChatMessage) and isinstance(msg2, BaseTextChatMessage):
        if msg1.content != msg2.content:
            return False
    return (
        (msg1.source == msg2.source) and (msg1.models_usage == msg2.models_usage) and (msg1.metadata == msg2.metadata)
    )


def compare_message_lists(
    msgs1: Sequence[BaseAgentEvent | BaseChatMessage],
    msgs2: Sequence[BaseAgentEvent | BaseChatMessage],
) -> bool:
    if len(msgs1) != len(msgs2):
        return False
    for i in range(len(msgs1)):
        if not compare_messages(msgs1[i], msgs2[i]):
            return False
    return True


def compare_task_results(
    res1: TaskResult,
    res2: TaskResult,
) -> bool:
    if res1.stop_reason != res2.stop_reason:
        return False
    return compare_message_lists(res1.messages, res2.messages)
