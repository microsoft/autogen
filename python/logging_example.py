"""
Logging Example for AutoGen AgentChat

Demonstrates how to enable and use trace and structured logging in AutoGen.
- Shows how to enable TRACE_LOGGER_NAME and EVENT_LOGGER_NAME loggers
- Shows how to add custom structured logging handlers
- Shows how to emit custom structured events

Requirements:
- autogen-agentchat, autogen-core

Run: python logging_example.py
"""
import logging
from dataclasses import dataclass

from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME
from autogen_core import EVENT_LOGGER_NAME as CORE_EVENT_LOGGER_NAME, TRACE_LOGGER_NAME as CORE_TRACE_LOGGER_NAME

# Enable basic logging for warnings and above
logging.basicConfig(level=logging.WARNING)

# Enable trace logging (human-readable debug output)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

# Enable structured event logging (machine-consumable events)
event_logger = logging.getLogger(EVENT_LOGGER_NAME)
event_logger.addHandler(logging.StreamHandler())
event_logger.setLevel(logging.DEBUG)

# Enable core trace and event loggers as well (for lower-level logs)
core_trace_logger = logging.getLogger(CORE_TRACE_LOGGER_NAME)
core_trace_logger.addHandler(logging.StreamHandler())
core_trace_logger.setLevel(logging.DEBUG)

core_event_logger = logging.getLogger(CORE_EVENT_LOGGER_NAME)
core_event_logger.addHandler(logging.StreamHandler())
core_event_logger.setLevel(logging.INFO)

# Example: Custom structured event and handler
@dataclass
class MyEvent:
    timestamp: str
    message: str

class MyHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, MyEvent):
                print(f"[STRUCTURED] Timestamp: {record.msg.timestamp}, Message: {record.msg.message}")
        except Exception:
            self.handleError(record)

# Attach custom handler to event logger
my_handler = MyHandler()
event_logger.handlers = [my_handler]
event_logger.setLevel(logging.INFO)

# Emit a custom structured event
event_logger.info(MyEvent("2026-04-26T12:00:00Z", "This is a structured log event."))

# Emit a trace log
trace_logger.debug("This is a trace log message.")

# Emit a core trace log
core_trace_logger.debug("This is a core trace log message.")

# Emit a core structured event
core_event_logger.info(MyEvent("2026-04-26T12:01:00Z", "This is a core structured log event."))

print("\nLogging example complete. Check your console output for log messages.")
