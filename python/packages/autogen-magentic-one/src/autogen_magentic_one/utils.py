import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Literal

from autogen_core import Image
from autogen_core.logging import LLMCallEvent

from .messages import (
    AgentEvent,
    AssistantContent,
    FunctionExecutionContent,
    OrchestrationEvent,
    SystemContent,
    UserContent,
    WebSurferEvent,
)


# Convert UserContent to a string
def message_content_to_str(
    message_content: UserContent | AssistantContent | SystemContent | FunctionExecutionContent,
) -> str:
    if isinstance(message_content, str):
        return message_content
    elif isinstance(message_content, List):
        converted: List[str] = list()
        for item in message_content:
            if isinstance(item, str):
                converted.append(item.rstrip())
            elif isinstance(item, Image):
                converted.append("<Image>")
            else:
                converted.append(str(item).rstrip())
        return "\n".join(converted)
    else:
        raise AssertionError("Unexpected response type.")


# MagenticOne log event handler
class LogHandler(logging.FileHandler):
    def __init__(self, filename: str = "log.jsonl") -> None:
        super().__init__(filename)
        self.logs_list: List[Dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).isoformat()
            if isinstance(record.msg, OrchestrationEvent):
                console_message = (
                    f"\n{'-'*75} \n" f"\033[91m[{ts}], {record.msg.source}:\033[0m\n" f"\n{record.msg.message}"
                )
                print(console_message, flush=True)
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "source": record.msg.source,
                        "message": record.msg.message,
                        "type": "OrchestrationEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, AgentEvent):
                console_message = (
                    f"\n{'-'*75} \n" f"\033[91m[{ts}], {record.msg.source}:\033[0m\n" f"\n{record.msg.message}"
                )
                print(console_message, flush=True)
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "source": record.msg.source,
                        "message": record.msg.message,
                        "type": "AgentEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, WebSurferEvent):
                console_message = f"\033[96m[{ts}], {record.msg.source}: {record.msg.message}\033[0m"
                print(console_message, flush=True)
                payload: Dict[str, Any] = {
                    "timestamp": ts,
                    "type": "WebSurferEvent",
                }
                payload.update(asdict(record.msg))
                record.msg = json.dumps(payload)
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
            elif isinstance(record.msg, LLMCallEvent):
                record.msg = json.dumps(
                    {
                        "timestamp": ts,
                        "prompt_tokens": record.msg.prompt_tokens,
                        "completion_tokens": record.msg.completion_tokens,
                        "type": "LLMCallEvent",
                    }
                )
                self.logs_list.append(json.loads(record.msg))
                super().emit(record)
        except Exception:
            self.handleError(record)


class SentinelMeta(type):
    """
    A baseclass for sentinels that plays well with type hints.
    Define new sentinels like this:

    ```
    class MY_DEFAULT(metaclass=SentinelMeta):
        pass


    foo: list[str] | None | type[MY_DEFAULT] = MY_DEFAULT
    ```

    Reference: https://stackoverflow.com/questions/69239403/type-hinting-parameters-with-a-sentinel-value-as-the-default
    """

    def __repr__(cls) -> str:
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        return False
