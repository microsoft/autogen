import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Union

from autogen_core.base import AgentId
from autogen_core.components import FunctionCall, Image
from autogen_core.components.models import FunctionExecutionResult

from ..agents import ChatMessage, MultiModalMessage, StopMessage, TextMessage, ToolCallMessage, ToolCallResultMessage
from ._events import ContentPublishEvent, SelectSpeakerEvent, ToolCallEvent, ToolCallResultEvent

TRACE_LOGGER_NAME = "autogen_agentchat"
EVENT_LOGGER_NAME = "autogen_agentchat.events"
ContentType = Union[str, List[Union[str, Image]], List[FunctionCall], List[FunctionExecutionResult]]


class BaseLogHandler(logging.Handler):
    def serialize_content(
        self,
        content: Union[ContentType, ChatMessage],
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
    def _format_chat_message(
        self,
        *,
        source_agent_id: AgentId | None,
        message: ChatMessage,
        timestamp: str,
    ) -> str:
        body = f"{self.serialize_content(message.content)}"
        if source_agent_id is None:
            console_message = f"\n{'-'*75} \n" f"\033[91m[{timestamp}]:\033[0m\n" f"\n{body}"
        else:
            # Display the source agent type rather than agent ID for better readability.
            # Also in AgentChat the agent type is unique for each agent.
            console_message = f"\n{'-'*75} \n" f"\033[91m[{timestamp}], {source_agent_id.type}:\033[0m\n" f"\n{body}"
        return console_message

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, ContentPublishEvent):
            sys.stdout.write(
                self._format_chat_message(
                    source_agent_id=record.msg.source,
                    message=record.msg.agent_message,
                    timestamp=ts,
                )
            )
            sys.stdout.flush()
        elif isinstance(record.msg, ToolCallEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Tool Call:\033[0m\n"
                f"\n{self.serialize_content(record.msg.agent_message)}"
            )
            sys.stdout.flush()
        elif isinstance(record.msg, ToolCallResultEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Tool Call Result:\033[0m\n"
                f"\n{self.serialize_content(record.msg.agent_message)}"
            )
            sys.stdout.flush()
        elif isinstance(record.msg, SelectSpeakerEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], {record.msg.source.type}:\033[0m\n"
                f"\nSelected next speaker: {record.msg.selected_speaker}"
            )
            sys.stdout.flush()
        else:
            raise ValueError(f"Unexpected log record: {record.msg}")


class FileLogHandler(BaseLogHandler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, ContentPublishEvent | ToolCallEvent | ToolCallResultEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "source": record.msg.source,
                    "agent_message": self.serialize_content(record.msg.agent_message),
                    "type": record.msg.__class__.__name__,
                },
                default=self.json_serializer,
            )
        elif isinstance(record.msg, SelectSpeakerEvent):
            log_entry = json.dumps(
                {
                    "timestamp": ts,
                    "source": record.msg.source,
                    "selected_speaker": record.msg.selected_speaker,
                    "type": "SelectSpeakerEvent",
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
