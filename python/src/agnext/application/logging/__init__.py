from ._llm_usage import LLMUsageTracker

ROOT_LOGGER_NAME = "agnext"
"""str: Logger name used for structured event logging"""

EVENT_LOGGER_NAME = "agnext.events"
"""str: Logger name used for structured event logging"""


TRACE_LOGGER_NAME = "agnext.trace"
"""str: Logger name used for developer intended trace logging. The content and format of this log should not be depended upon."""

__all__ = [
    "ROOT_LOGGER_NAME",
    "EVENT_LOGGER_NAME",
    "TRACE_LOGGER_NAME",
    "LLMUsageTracker",
]
