"""Auto-recovery wrapper for chat completion clients with configurable retry logic."""

from ._retry_chat_completion_client import RetryableChatCompletionClient, RetryConfig

__all__ = [
    "RetryableChatCompletionClient",
    "RetryConfig",
]
