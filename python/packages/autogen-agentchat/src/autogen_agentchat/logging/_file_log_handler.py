import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from ..agents._assistant_agent import ToolCallEvent, ToolCallResultEvent
from ..teams._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
    TerminationEvent,
)


class FileLogHandler(logging.Handler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, GroupChatPublishEvent | TerminationEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "source": record.msg.source,
                    "agent_message": record.msg.agent_message.model_dump(),
                    "type": record.msg.__class__.__name__,
                },
                default=self.json_serializer,
            )
        elif isinstance(record.msg, GroupChatSelectSpeakerEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "source": record.msg.source,
                    "selected_speaker": record.msg.selected_speaker,
                    "type": "SelectSpeakerEvent",
                },
                default=self.json_serializer,
            )
        elif isinstance(record.msg, ToolCallEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "tool_calls": record.msg.model_dump(),
                    "type": "ToolCallEvent",
                },
                default=self.json_serializer,
            )
        elif isinstance(record.msg, ToolCallResultEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "tool_call_results": record.msg.model_dump(),
                    "type": "ToolCallResultEvent",
                },
                default=self.json_serializer,
            )
        else:
            raise ValueError(f"Unexpected log record: {record.msg}")
        file_record = logging.LogRecord(
            name=record.name,
            level=record.levelno,
            pathname=record.pathname,
            lineno=record.lineno,
            msg=log_entry,
            args=(),
            exc_info=record.exc_info,
        )
        self.file_handler.emit(file_record)

    def close(self) -> None:
        self.file_handler.close()
        super().close()

    @staticmethod
    def json_serializer(obj: Any) -> Any:
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        elif isinstance(obj, type):
            return str(obj)
        return str(obj)
