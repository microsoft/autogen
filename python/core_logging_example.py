"""
core_logging_example.py

Demonstrates logging in AutoGen Core:
- Trace logging (human-readable, for debugging)
- Structured logging (machine-consumable events)
- Custom structured event and handler
- Emitting logs from a child logger

To run:
    python core_logging_example.py
"""
import logging
from dataclasses import dataclass
from datetime import datetime

try:
    from autogen_core import TRACE_LOGGER_NAME, EVENT_LOGGER_NAME
except ImportError:
    # Fallback for doc/test if autogen_core is not installed
    TRACE_LOGGER_NAME = "autogen_core.trace"
    EVENT_LOGGER_NAME = "autogen_core.event"

# --- Enable trace logging ---
logging.basicConfig(level=logging.WARNING)
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

# --- Enable structured logging ---
event_logger = logging.getLogger(EVENT_LOGGER_NAME)
event_logger.addHandler(logging.StreamHandler())
event_logger.setLevel(logging.INFO)

# --- Custom structured event ---
@dataclass
class MyEvent:
    timestamp: str
    message: str

# --- Custom handler for structured events ---
class MyHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            if isinstance(record.msg, MyEvent):
                print(f"[STRUCTURED] Timestamp: {record.msg.timestamp}, Message: {record.msg.message}")
        except Exception:
            self.handleError(record)

# Attach custom handler for demonstration
custom_event_logger = logging.getLogger(EVENT_LOGGER_NAME + ".custom")
custom_event_logger.setLevel(logging.INFO)
my_handler = MyHandler()
custom_event_logger.handlers = [my_handler]

# --- Emitting logs ---
def main():
    print("\n--- Trace Logging Example ---")
    trace_logger.debug("This is a trace log (debug level)")
    trace_logger.info("This is a trace log (info level)")
    trace_logger.warning("This is a trace log (warning level)")

    print("\n--- Structured Logging Example ---")
    event_logger.info(MyEvent(timestamp=datetime.now().isoformat(), message="Structured event log!"))

    print("\n--- Custom Structured Handler Example ---")
    custom_event_logger.info(MyEvent(timestamp=datetime.now().isoformat(), message="Custom structured event!"))

    print("\n--- Emitting logs from child logger ---")
    child_logger = logging.getLogger(f"{TRACE_LOGGER_NAME}.my_module")
    child_logger.debug("Trace log from my_module")
    child_event_logger = logging.getLogger(EVENT_LOGGER_NAME + ".my_module")
    child_event_logger.info(MyEvent(timestamp=datetime.now().isoformat(), message="Structured event from my_module!"))

if __name__ == "__main__":
    main()
