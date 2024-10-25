import json
import logging
import sys
from datetime import datetime

from ..agents._tool_use_assistant_agent import ToolCallEvent, ToolCallResultEvent
from ..messages import ChatMessage, StopMessage, TextMessage
from ..teams._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
    TerminationEvent,
)


class ConsoleLogHandler(logging.Handler):
    @staticmethod
    def serialize_chat_message(message: ChatMessage) -> str:
        if isinstance(message, TextMessage | StopMessage):
            return message.content
        else:
            d = message.model_dump()
            assert "content" in d
            return json.dumps(d["content"], indent=2)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, GroupChatPublishEvent):
            if record.msg.source is None:
                sys.stdout.write(
                    f"\n{'-'*75} \n"
                    f"\033[91m[{ts}]:\033[0m\n"
                    f"\n{self.serialize_chat_message(record.msg.agent_message)}"
                )
            else:
                sys.stdout.write(
                    f"\n{'-'*75} \n"
                    f"\033[91m[{ts}], {record.msg.source.type}:\033[0m\n"
                    f"\n{self.serialize_chat_message(record.msg.agent_message)}"
                )
            sys.stdout.flush()
        elif isinstance(record.msg, ToolCallEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n" f"\033[91m[{ts}], Tool Call:\033[0m\n" f"\n{str(record.msg.model_dump())}"
            )
            sys.stdout.flush()
        elif isinstance(record.msg, ToolCallResultEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n" f"\033[91m[{ts}], Tool Call Result:\033[0m\n" f"\n{str(record.msg.model_dump())}"
            )
            sys.stdout.flush()
        elif isinstance(record.msg, GroupChatSelectSpeakerEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n" f"\033[91m[{ts}], Selected Next Speaker:\033[0m\n" f"\n{record.msg.selected_speaker}"
            )
            sys.stdout.flush()
        elif isinstance(record.msg, TerminationEvent):
            sys.stdout.write(
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Termination:\033[0m\n"
                f"\n{self.serialize_chat_message(record.msg.agent_message)}"
            )
            sys.stdout.flush()
        else:
            raise ValueError(f"Unexpected log record: {record.msg}")
