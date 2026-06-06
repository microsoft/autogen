"""
This module provides the MessageStore abstraction for storing message threads in teams.
"""

from ._message_store import InMemoryMessageStore, MessageStore

__all__ = ["MessageStore", "InMemoryMessageStore"]
