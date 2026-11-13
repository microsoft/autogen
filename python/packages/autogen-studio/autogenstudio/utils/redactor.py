import os
import re
from typing import Any, List, Optional, Union

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    HandoffMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    StopMessage,
    TextMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)

from ..datamodel.types import EnvironmentVariable, LLMCallEventMessage, RedactionConfig, TeamResult

# Built-in regex patterns for sensitive credentials
DEFAULT_SENSITIVE_PATTERNS = [
    # OpenAI API keys (legacy and project-scoped)
    r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,})\b",
    # Anthropic API keys
    r"\b(?:sk-ant-[A-Za-z0-9_-]{20,})\b",
    # GitHub personal access / OAuth tokens
    r"\b(?:gh[pousr][_-][A-Za-z0-9_]{20,})\b",
    # AWS Access Key IDs
    r"\b(?:AKIA[0-9A-Z]{16})\b",
    # Bearer tokens (redacts the token secret)
    r"(?i)\bBearer\s+[A-Za-z0-9\-_.~+/]{20,}\b",
    # Azure storage / service keys
    r"(?i)(?:AccountKey=[A-Za-z0-9+/=]{40,})",
    # Generic Private Key blocks
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[^-]+-----END [A-Z ]+ PRIVATE KEY-----",
]

SENSITIVE_ENV_KEYWORDS = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "APIKEY",
    "AUTH",
    "PRIVATE",
)


class SensitiveDataRedactor:
    """Sanitizes sensitive information (PII, credentials, API keys) from agent responses."""

    def __init__(
        self,
        config: Optional[RedactionConfig] = None,
        env_vars: Optional[List[EnvironmentVariable]] = None,
    ) -> None:
        self.config = config or RedactionConfig()
        self.replacement = self.config.replacement

        self._literal_secrets: List[str] = []
        self._compiled_patterns: List[re.Pattern[str]] = []

        if not self.config.enabled:
            return

        # 1. Compile API key patterns
        if self.config.redact_api_keys:
            for pat in DEFAULT_SENSITIVE_PATTERNS:
                try:
                    self._compiled_patterns.append(re.compile(pat))
                except re.error:
                    pass

        # 2. Compile custom user patterns
        for pat in self.config.custom_patterns:
            try:
                self._compiled_patterns.append(re.compile(pat))
            except re.error:
                pass

        # 3. Collect literal secrets from environment variables
        if self.config.redact_env_vars:
            raw_secrets: set[str] = set()

            if env_vars:
                for var in env_vars:
                    is_secret_type = var.type == "secret"
                    name_has_secret = any(kw in var.name.upper() for kw in SENSITIVE_ENV_KEYWORDS)
                    if (is_secret_type or name_has_secret) and var.value and len(var.value.strip()) >= 4:
                        raw_secrets.add(var.value.strip())

            # Also check os.environ for matching secret keys
            for key, val in os.environ.items():
                if any(kw in key.upper() for kw in SENSITIVE_ENV_KEYWORDS) and val and len(val.strip()) >= 8:
                    raw_secrets.add(val.strip())

            # Sort by length descending to replace longest secrets first
            self._literal_secrets = sorted(raw_secrets, key=len, reverse=True)

    def redact_text(self, text: Optional[str]) -> str:
        """Redact sensitive information from a text string."""
        if not self.config.enabled or not text or not isinstance(text, str):
            return text or ""

        # Step 1: Replace literal secrets
        for secret in self._literal_secrets:
            text = text.replace(secret, self.replacement)

        # Step 2: Apply regex patterns
        for pattern in self._compiled_patterns:
            text = pattern.sub(self.replacement, text)

        return text

    def redact_dict(self, obj: Any) -> Any:
        """Recursively redact sensitive data in dictionaries, lists, and strings."""
        if not self.config.enabled:
            return obj

        if isinstance(obj, str):
            return self.redact_text(obj)
        elif isinstance(obj, dict):
            return {k: self.redact_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.redact_dict(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self.redact_dict(item) for item in obj)
        return obj

    def redact_message(
        self, message: Union[BaseAgentEvent, BaseChatMessage, Any]
    ) -> Union[BaseAgentEvent, BaseChatMessage, Any]:
        """Redact sensitive information from message models and events."""
        if not self.config.enabled:
            return message

        if isinstance(message, (TextMessage, StopMessage, HandoffMessage)):
            redacted_content = self.redact_text(message.content)
            redacted_meta = self.redact_dict(message.metadata) if hasattr(message, "metadata") else None
            if hasattr(message, "model_copy"):
                update_dict: dict[str, Any] = {"content": redacted_content}
                if redacted_meta is not None:
                    update_dict["metadata"] = redacted_meta
                return message.model_copy(update=update_dict)

        elif isinstance(message, MultiModalMessage):
            redacted_content = []
            for item in message.content:
                if isinstance(item, str):
                    redacted_content.append(self.redact_text(item))
                else:
                    redacted_content.append(item)
            redacted_meta = self.redact_dict(message.metadata) if hasattr(message, "metadata") else None
            if hasattr(message, "model_copy"):
                update_dict = {"content": redacted_content}
                if redacted_meta is not None:
                    update_dict["metadata"] = redacted_meta
                return message.model_copy(update=update_dict)

        elif isinstance(message, LLMCallEventMessage):
            redacted_content = self.redact_text(message.content)
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"content": redacted_content})

        elif isinstance(message, ModelClientStreamingChunkEvent):
            redacted_content = self.redact_text(message.content)
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"content": redacted_content})

        elif isinstance(message, ToolCallRequestEvent):
            redacted_calls = []
            for call in message.content:
                if hasattr(call, "arguments") and isinstance(call.arguments, str):
                    redacted_args = self.redact_text(call.arguments)
                    if hasattr(call, "model_copy"):
                        redacted_calls.append(call.model_copy(update={"arguments": redacted_args}))
                    else:
                        redacted_calls.append(call)
                else:
                    redacted_calls.append(call)
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"content": redacted_calls})

        elif isinstance(message, ToolCallExecutionEvent):
            redacted_results = []
            for res in message.content:
                if hasattr(res, "content") and isinstance(res.content, str):
                    redacted_res_content = self.redact_text(res.content)
                    if hasattr(res, "model_copy"):
                        redacted_results.append(res.model_copy(update={"content": redacted_res_content}))
                    else:
                        redacted_results.append(res)
                else:
                    redacted_results.append(res)
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"content": redacted_results})

        elif isinstance(message, TaskResult):
            redacted_messages = [self.redact_message(m) for m in message.messages]
            redacted_stop_reason = self.redact_text(message.stop_reason) if message.stop_reason else None
            if hasattr(message, "model_copy"):
                return message.model_copy(
                    update={"messages": redacted_messages, "stop_reason": redacted_stop_reason}
                )

        elif isinstance(message, TeamResult):
            redacted_tr = self.redact_message(message.task_result)
            redacted_usage = self.redact_text(message.usage) if message.usage else ""
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"task_result": redacted_tr, "usage": redacted_usage})

        # Generic fallback for any object with content
        if hasattr(message, "content") and isinstance(message.content, str):
            if hasattr(message, "model_copy"):
                return message.model_copy(update={"content": self.redact_text(message.content)})

        return message
