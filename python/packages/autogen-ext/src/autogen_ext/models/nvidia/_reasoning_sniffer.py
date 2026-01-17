# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""High-speed regex-based Intent Sniffer for Speculative Reasoning Execution.

This module provides zero-latency heuristic detection of tool-call intents
within streaming reasoning content from DeepSeek-R1 and similar models.
The sniffer runs on every chunk without blocking the stream.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern


@dataclass
class ToolIntent:
    """Represents a detected tool-call intent from reasoning content."""

    tool_type: str
    """The type/name of the tool detected (e.g., 'web_search', 'database_query')."""

    query_hint: str
    """Extracted query or argument hint from the reasoning."""

    confidence: float
    """Confidence score (0.0 to 1.0) based on pattern match strength."""

    detected_at_ms: float
    """Timestamp when the intent was detected (perf_counter * 1000)."""

    reasoning_context: str
    """The chunk of reasoning text that triggered the detection."""


@dataclass
class ReasoningSniffer:
    """Detects tool-call intents in streaming reasoning content.

    Uses high-speed regex patterns to identify when the model is planning
    to use a specific tool. Designed to run on every streaming chunk
    without introducing latency.

    Example:
        >>> sniffer = ReasoningSniffer()
        >>> intent = sniffer.sniff("I will search for Python documentation")
        >>> if intent:
        ...     print(f"Detected {intent.tool_type}: {intent.query_hint}")
        Detected web_search: Python documentation
    """

    # High-signal patterns for DeepSeek-R1's "Action Intent"
    # These are tuned for common reasoning patterns in R1-style models
    # Enhanced to catch contractions (I'll, I'd) and more natural phrasings
    PATTERNS: Dict[str, str] = field(
        default_factory=lambda: {
            # Web search intents - extended with contractions and more verbs
            "web_search": r"(?:I(?:'ll| will| need to| should| must| have to)|Let me|I'd like to|need to)?\s*(?:search|look up|find|query|google|browse|look for|check online|research|find out|look into)\s+(?:for\s+|about\s+|the\s+|on\s+)?(?:information\s+(?:about|on)\s+)?['\"]?(.+?)(?:['\"]|\\.|,|;|$)",
            # Database query intents
            "database_query": r"(?:I(?:'ll| will| need to| should)|Let me)\s*(?:query|check|access|look up in|fetch from|retrieve from)\s+(?:the\s+)?(?:database|db|table|records?)\s+(?:for\s+)?['\"]?(.+?)(?:['\"]|\\.|,|$)",
            # Calculation intents
            "calculate": r"(?:I(?:'ll| will| need to| should)|Let me)\s*(?:calculate|compute|evaluate|work out|figure out|determine)\s+(.+?)(?:\\.|,|$)",
            # API call intents
            "api_call": r"(?:I(?:'ll| will| need to| should)|Let me)\s*(?:call|invoke|use|hit|query|fetch from)\s+(?:the\s+)?(?:API|endpoint|service|REST)\s+(?:for\s+)?['\"]?(.+?)(?:['\"]|\\.|,|$)",
            # File/document lookup intents
            "file_lookup": r"(?:I(?:'ll| will| need to| should)|Let me)\s*(?:read|open|check|look at|load|parse)\s+(?:the\s+)?(?:file|document|config|data)\s+['\"]?(.+?)(?:['\"]|\\.|,|$)",
            # Generic tool usage
            "tool_use": r"(?:I(?:'ll| will| need to| should)|Let me)\s*(?:use|invoke|call|execute)\s+(?:the\s+)?[`'\"]?(\w+)[`'\"]?\s+(?:tool|function)",
        }
    )

    # Compiled patterns for performance
    _compiled_patterns: Dict[str, Pattern[str]] = field(default_factory=dict)

    # Buffer for accumulating reasoning context
    _context_buffer: List[str] = field(default_factory=list)
    _max_buffer_size: int = 500  # Characters to keep for context

    def __post_init__(self) -> None:
        """Compile regex patterns for maximum performance."""
        self._compiled_patterns = {
            tool_type: re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for tool_type, pattern in self.PATTERNS.items()
        }

    def add_pattern(self, tool_type: str, pattern: str) -> None:
        """Add a custom pattern for detecting a specific tool type.

        Args:
            tool_type: The name/type of the tool to detect.
            pattern: Regex pattern with a capture group for the query hint.
        """
        self.PATTERNS[tool_type] = pattern
        self._compiled_patterns[tool_type] = re.compile(
            pattern, re.IGNORECASE | re.DOTALL
        )

    def sniff(self, text: str) -> Optional[ToolIntent]:
        """Analyze a chunk of reasoning text for tool-call intents.

        This method is designed to be called on every streaming chunk.
        It maintains an internal buffer to provide context for pattern matching.

        Args:
            text: A chunk of reasoning text from the model's thought stream.

        Returns:
            ToolIntent if an intent was detected, None otherwise.
        """
        if not text or not text.strip():
            return None

        # Add to context buffer
        self._context_buffer.append(text)

        # Keep buffer size manageable
        full_context = "".join(self._context_buffer)
        if len(full_context) > self._max_buffer_size:
            # Trim from the beginning
            excess = len(full_context) - self._max_buffer_size
            self._context_buffer = [full_context[excess:]]

        # Scan the current chunk and recent context
        search_text = full_context[-self._max_buffer_size :]

        for tool_type, compiled_pattern in self._compiled_patterns.items():
            match = compiled_pattern.search(search_text)
            if match:
                query_hint = match.group(1).strip() if match.lastindex else ""
                # Calculate confidence based on match quality
                confidence = self._calculate_confidence(match, search_text)

                return ToolIntent(
                    tool_type=tool_type,
                    query_hint=query_hint,
                    confidence=confidence,
                    detected_at_ms=time.perf_counter() * 1000,
                    reasoning_context=search_text[-200:],  # Last 200 chars for context
                )

        return None

    def _calculate_confidence(self, match: re.Match[str], text: str) -> float:
        """Calculate confidence score based on match characteristics.

        Args:
            match: The regex match object.
            text: The full text being searched.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        confidence = 0.7  # Base confidence for any match

        # Boost if match is recent (in the last 100 chars)
        if match.end() > len(text) - 100:
            confidence += 0.15

        # Boost if query hint is substantial
        if match.lastindex and len(match.group(1).strip()) > 5:
            confidence += 0.1

        # Boost if explicit tool mention
        if "tool" in text.lower() or "function" in text.lower():
            confidence += 0.05

        return min(confidence, 1.0)

    def reset(self) -> None:
        """Reset the context buffer. Call this between separate reasoning sessions."""
        self._context_buffer.clear()
