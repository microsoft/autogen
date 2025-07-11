"""
This module provides the main entry point for the autogen_agentchat package.
It includes logger names for trace and event logs, and retrieves the package version.
"""

import importlib.metadata

TRACE_LOGGER_NAME = "autogen_agentchat"
"""Logger name for trace logs."""

EVENT_LOGGER_NAME = "autogen_agentchat.events"
"""Logger name for event logs."""

try:
    __version__ = importlib.metadata.version("autogen_agentchat")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.6.4"  # Fallback version for development
