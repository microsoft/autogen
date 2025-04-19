"""
This module provides implementation of various pre-defined multi-agent teams.
Each team inherits from the BaseGroupChat class.
"""

from ._group_chat._base_group_chat import BaseGroupChat
from ._group_chat._graph import (
    AGGraphBuilder,
    DiGraphGroupChat,
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from ._group_chat._magentic_one import MagenticOneGroupChat
from ._group_chat._round_robin_group_chat import RoundRobinGroupChat
from ._group_chat._selector_group_chat import SelectorGroupChat
from ._group_chat._swarm_group_chat import Swarm

__all__ = [
    "BaseGroupChat",
    "RoundRobinGroupChat",
    "SelectorGroupChat",
    "Swarm",
    "MagenticOneGroupChat",
    "AGGraphBuilder",
    "MessageFilterAgent",
    "MessageFilterConfig",
    "PerSourceFilter",
    "DiGraphGroupChat",
]
