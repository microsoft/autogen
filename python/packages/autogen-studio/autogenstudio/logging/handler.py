import logging
import sys
from datetime import datetime
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict
from autogen_agentchat.messages import ChatMessage, StopMessage, TextMessage
from autogen_agentchat.agents._assistant_agent import ToolCallEvent, ToolCallResultEvent
from autogen_agentchat.teams._events import (
    GroupChatPublishEvent,
    GroupChatSelectSpeakerEvent,
    TerminationEvent
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
                console_msg = (
                    f"\n{'-'*75} \n"
                    f"\033[91m[{ts}]:\033[0m\n"
                    f"\n{self.serialize_chat_message(record.msg.agent_message)}"
                )
            else:
                console_msg = (
                    f"\n{'-'*75} \n"
                    f"\033[91m[{ts}], {record.msg.source.type}:\033[0m\n"
                    f"\n{self.serialize_chat_message(record.msg.agent_message)}"
                )
        elif isinstance(record.msg, ToolCallEvent):
            console_msg = (
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Tool Call:\033[0m\n"
                f"\n{str(record.msg.model_dump())}"
            )
        elif isinstance(record.msg, ToolCallResultEvent):
            console_msg = (
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Tool Call Result:\033[0m\n"
                f"\n{str(record.msg.model_dump())}"
            )
        elif isinstance(record.msg, GroupChatSelectSpeakerEvent):
            console_msg = (
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Selected Next Speaker:\033[0m\n"
                f"\n{record.msg.selected_speaker}"
            )
        elif isinstance(record.msg, TerminationEvent):
            console_msg = (
                f"\n{'-'*75} \n"
                f"\033[91m[{ts}], Termination:\033[0m\n"
                f"\n{self.serialize_chat_message(record.msg.agent_message)}"
            )
        else:
            raise ValueError(f"Unexpected log record: {record.msg}")

        sys.stdout.write(console_msg)
        sys.stdout.flush()


class WebSocketLogHandler(logging.Handler):
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        self.context = {}

    @asynccontextmanager
    async def session_context(self, session_id: str):
        """Context manager to set the current session ID"""
        task = asyncio.current_task()
        self.context[task] = session_id
        try:
            yield
        finally:
            self.context.pop(task, None)

    def get_current_session(self) -> Optional[str]:
        """Get the session ID for the current task"""
        task = asyncio.current_task()
        return self.context.get(task)

    @staticmethod
    def serialize_chat_message(message: ChatMessage) -> str:
        if isinstance(message, TextMessage | StopMessage):
            return message.content
        else:
            d = message.model_dump()
            assert "content" in d
            return json.dumps(d["content"], indent=2)

    def format_log_event(self, record: logging.LogRecord) -> Dict:
        ts = datetime.fromtimestamp(record.created).isoformat()

        event = {
            "timestamp": ts,
            "type": record.msg.__class__.__name__
        }

        if isinstance(record.msg, GroupChatPublishEvent):
            event.update({
                "content": self.serialize_chat_message(record.msg.agent_message),
                "source": record.msg.source.type if record.msg.source else None
            })
        elif isinstance(record.msg, (ToolCallEvent, ToolCallResultEvent)):
            event.update({
                "content": str(record.msg.model_dump())
            })
        elif isinstance(record.msg, GroupChatSelectSpeakerEvent):
            event.update({
                "content": record.msg.selected_speaker
            })
        elif isinstance(record.msg, TerminationEvent):
            event.update({
                "content": self.serialize_chat_message(record.msg.agent_message)
            })
        else:
            raise ValueError(f"Unexpected log record: {record.msg}")

        return event

    def emit(self, record: logging.LogRecord) -> None:
        session_id = self.get_current_session()
        if session_id:
            ws_message = self.format_log_event(record)
            asyncio.create_task(
                self.connection_manager.send_to_session(
                    session_id,
                    json.dumps(ws_message)
                )
            )
