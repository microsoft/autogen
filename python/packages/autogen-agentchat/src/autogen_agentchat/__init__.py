"""
This module provides the main entry point for the autogen_agentchat package.
It includes logger names for trace and event logs, and retrieves the package version.
"""
#from .agents._assistant_agent import AssistantAgent
from .utils.constants import EVENT_LOGGER_NAME
# autogen_agentchat/__init__.py
from .agents._assistant_agent import AssistantAgent

import importlib.metadata

TRACE_LOGGER_NAME = "autogen_agentchat"
"""Logger name for trace logs."""

EVENT_LOGGER_NAME = "autogen_agentchat.events"
"""Logger name for event logs."""

__version__ = importlib.metadata.version("autogen_agentchat")
