"""
This module provides the main entry point for the autogen_agentchat package.
It includes logger names for trace and event logs, and retrieves the package version.
"""

import importlib.metadata

# Export approval guard components
from .approval_guard import ApprovalConfig, ApprovalGuard, BaseApprovalGuard
from .guarded_action import ApprovalDeniedError, TrivialGuardedAction
from .input_func import AsyncInputFunc, InputFuncType, SyncInputFunc

TRACE_LOGGER_NAME = "autogen_agentchat"
"""Logger name for trace logs."""

EVENT_LOGGER_NAME = "autogen_agentchat.events"
"""Logger name for event logs."""

__version__ = "0.0.0"  # Default version
try:
    __version__ = importlib.metadata.version("autogen_agentchat")
except importlib.metadata.PackageNotFoundError:
    pass  # Use default version when package is not installed

__all__ = [
    "ApprovalGuard",
    "BaseApprovalGuard",
    "ApprovalConfig",
    "ApprovalDeniedError",
    "TrivialGuardedAction",
    "InputFuncType",
    "AsyncInputFunc",
    "SyncInputFunc",
    "TRACE_LOGGER_NAME",
    "EVENT_LOGGER_NAME",
]
