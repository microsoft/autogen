import importlib.metadata

TRACE_LOGGER_NAME = "autogen_agentchat"
"""Logger name for trace logs."""

EVENT_LOGGER_NAME = "autogen_agentchat.events"
"""Logger name for event logs."""

__version__ = importlib.metadata.version("autogen_agentchat")
