from datetime import datetime
import json
import logging
import sys
from typing import Union, List, Dict, Any, Sequence
from dataclasses import asdict, is_dataclass

from .group_chat._events import ContentPublishEvent
from ..agents import ChatMessage, TextMessage, MultiModalMessage, ToolCallMessage, ToolCallResultMessage, StopMessage
from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult

EVENT_LOGGER_NAME = "autogen_agentchat.events"
ContentType = Union[str, List[Union[str, Image]], List[FunctionCall], List[FunctionExecutionResult]]


class BaseLogHandler(logging.Handler):
    def serialize_content(
        self, content: Union[ContentType, Sequence[ChatMessage], ChatMessage]
    ) -> Union[List[Any], Dict[str, Any], str]:
        if isinstance(content, (str, list)):
            return content
        elif isinstance(content, (TextMessage, MultiModalMessage, ToolCallMessage, ToolCallResultMessage, StopMessage)):
            return asdict(content)
        elif isinstance(content, Image):
            return {"type": "image", "data": content.data_uri}
        elif isinstance(content, FunctionCall):
            return {"type": "function_call", "name": content.name, "arguments": content.arguments}
        elif isinstance(content, FunctionExecutionResult):
            return {"type": "function_execution_result", "content": content.content}
        return str(content)

    @staticmethod
    def json_serializer(obj: Any) -> Any:
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        elif isinstance(obj, type):
            return str(obj)
        return str(obj)


class ConsoleLogHandler(BaseLogHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).isoformat()
            if isinstance(record.msg, ContentPublishEvent):
                console_message = (
                    f"\n{'-'*75} \n"
                    f"\033[91m[{ts}], {record.msg.agent_message.source}:\033[0m\n"
                    f"\n{self.serialize_content(record.msg.agent_message.content)}"
                )
                sys.stdout.write(console_message)
                sys.stdout.flush()
        except Exception:
            self.handleError(record)


class FileLogHandler(BaseLogHandler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).isoformat()
            if isinstance(record.msg, ContentPublishEvent):
                log_entry = json.dumps(
                    {
                        "timestamp": ts,
                        "source": record.msg.agent_message.source,
                        "message": self.serialize_content(record.msg.agent_message.content),
                        "type": "OrchestrationEvent",
                    },
                    default=self.json_serializer,
                )

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
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.file_handler.close()
        super().close()
