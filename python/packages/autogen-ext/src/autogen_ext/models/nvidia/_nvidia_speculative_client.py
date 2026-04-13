# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""NVIDIA NIM Speculative Reasoning Execution Client for AutoGen 0.4.

This module provides the main ChatCompletionClient implementation that bridges
NVIDIA NIM inference with AutoGen orchestration. It enables parallel tool
execution during LLM reasoning to dramatically reduce "Time to Action" latency.

Key Features:
- Streams DeepSeek-R1 style <think>...</think> reasoning blocks
- Uses ReasoningSniffer to detect tool intents during reasoning
- Fires speculative prewarm tasks via asyncio.create_task (non-blocking)
- Logs high-precision latency metrics for benchmarking

The "Shark" Architecture:
    Model thinks → Sniffer detects intent → Prewarm fires (background)
                                         → Model keeps thinking
                                         → Tool actually called → Cache HIT
"""

from __future__ import annotations

import asyncio
import logging
import time
import warnings
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Union,
)

from autogen_core import CancellationToken
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
)
from autogen_core.models._model_client import ModelFamily
from autogen_core.tools import Tool, ToolSchema

from ._reasoning_sniffer import ReasoningSniffer, ToolIntent
from ._speculative_cache import SpeculativeCache

# Event logger for LLM events
EVENT_LOGGER_NAME = "autogen_core.events"
logger = logging.getLogger(EVENT_LOGGER_NAME)
trace_logger = logging.getLogger(__name__)


@dataclass
class SpeculativePrewarmEvent:
    """Event emitted when the ReasoningSniffer detects a tool intent.

    This event is logged to the event bus so that orchestrators can
    trigger speculative tool execution.
    """

    tool_type: str
    """The type/name of the tool detected."""

    query_hint: str
    """Extracted query or argument hint from the reasoning."""

    confidence: float
    """Confidence score (0.0 to 1.0)."""

    detected_at_ms: float
    """Timestamp when the intent was detected."""

    reasoning_context: str
    """The reasoning text that triggered detection."""

    def __str__(self) -> str:
        return (
            f"SpeculativePrewarm: tool={self.tool_type}, "
            f"hint='{self.query_hint[:50]}...', confidence={self.confidence:.2f}"
        )


@dataclass
class SpeculativeHitEvent:
    """Event emitted when a cached speculative result is used."""

    tool_name: str
    """Name of the tool that had a cache hit."""

    latency_saved_ms: float
    """Estimated latency saved by using the cached result."""

    def __str__(self) -> str:
        return (
            f"SpeculativeHit: tool={self.tool_name}, "
            f"latency_saved={self.latency_saved_ms:.1f}ms"
        )


@dataclass
class PerformanceMetrics:
    """Performance tracking for the speculative execution pipeline."""

    stream_start_time: float = 0.0
    first_token_time: Optional[float] = None
    reasoning_start_time: Optional[float] = None
    reasoning_end_time: Optional[float] = None
    first_intent_detected_time: Optional[float] = None
    tool_call_time: Optional[float] = None
    stream_end_time: float = 0.0

    intents_detected: int = 0
    prewarms_triggered: int = 0

    @property
    def ttft_ms(self) -> Optional[float]:
        """Time to first token in milliseconds."""
        if self.first_token_time is None:
            return None
        return (self.first_token_time - self.stream_start_time) * 1000

    @property
    def reasoning_duration_ms(self) -> Optional[float]:
        """Total reasoning duration in milliseconds."""
        if self.reasoning_start_time is None or self.reasoning_end_time is None:
            return None
        return (self.reasoning_end_time - self.reasoning_start_time) * 1000

    @property
    def speculative_delta_ms(self) -> Optional[float]:
        """The 'speculative delta' - how early we detected intent vs tool call.

        Negative = we detected before the model called (good!)
        Positive = we missed the window (speculation opportunity lost)
        """
        if self.first_intent_detected_time is None or self.tool_call_time is None:
            return None
        return (self.tool_call_time - self.first_intent_detected_time) * 1000

    def summary(self) -> Dict[str, Any]:
        """Get a summary of all performance metrics."""
        return {
            "ttft_ms": self.ttft_ms,
            "reasoning_duration_ms": self.reasoning_duration_ms,
            "speculative_delta_ms": self.speculative_delta_ms,
            "intents_detected": self.intents_detected,
            "prewarms_triggered": self.prewarms_triggered,
            "total_duration_ms": (self.stream_end_time - self.stream_start_time) * 1000,
        }


# Type alias for the prewarm callback
PrewarmCallback = Callable[[str, str, Dict[str, Any]], Awaitable[Any]]


class NvidiaSpeculativeClient(ChatCompletionClient):
    """NVIDIA NIM-compatible ChatCompletionClient with Speculative Reasoning Execution.

    This client wraps an existing OpenAI-compatible client (which connects to
    NVIDIA NIM, vLLM, or any OpenAI-compatible endpoint) and adds speculative
    execution capabilities.

    The key innovation is that during the model's reasoning phase (<think> block),
    the ReasoningSniffer monitors for tool-call intents. When detected, it triggers
    a prewarm callback to speculatively execute the tool in the background.

    Args:
        inner_client: An existing ChatCompletionClient (e.g., OpenAIChatCompletionClient
            configured for NIM endpoint).
        sniffer: Optional custom ReasoningSniffer. Uses default patterns if not provided.
        prewarm_callback: Async function called when tool intent is detected.
            Signature: async def callback(tool_type: str, query_hint: str, context: dict) -> Any
        enable_speculation: Whether to enable speculative execution (default: True).
        min_confidence: Minimum confidence threshold to trigger prewarm (default: 0.7).

    Example:
        >>> from autogen_ext.models.openai import OpenAIChatCompletionClient
        >>> from autogen_ext.models.nvidia import NvidiaSpeculativeClient
        >>>
        >>> # Create inner client pointing to NIM
        >>> inner = OpenAIChatCompletionClient(
        ...     model="deepseek-r1",
        ...     base_url="http://wulver:8000/v1",
        ...     api_key="token"
        ... )
        >>>
        >>> # Wrap with speculative execution
        >>> client = NvidiaSpeculativeClient(
        ...     inner_client=inner,
        ...     prewarm_callback=my_prewarm_function
        ... )
    """

    component_type = "model"
    component_config_schema = None  # TODO: Add proper config schema

    def __init__(
        self,
        inner_client: ChatCompletionClient,
        *,
        sniffer: Optional[ReasoningSniffer] = None,
        prewarm_callback: Optional[PrewarmCallback] = None,
        enable_speculation: bool = True,
        min_confidence: float = 0.7,
        sniff_all_content: bool = False,
    ) -> None:
        self._inner_client = inner_client
        self._sniffer = sniffer or ReasoningSniffer()
        self._prewarm_callback = prewarm_callback
        self._enable_speculation = enable_speculation
        self._min_confidence = min_confidence
        self._sniff_all_content = sniff_all_content  # For distilled models without <think> tags
        self._cache = SpeculativeCache.get_instance()

        # Track running prewarm tasks
        self._prewarm_tasks: List[asyncio.Task[Any]] = []

        # DEDUPLICATION: Track triggered intents to avoid firing 78 times
        self._triggered_intents: set[str] = set()

        # Performance tracking
        self._last_metrics: Optional[PerformanceMetrics] = None

    @property
    def model_info(self) -> ModelInfo:
        """Get model info from the inner client."""
        return self._inner_client.model_info

    @property
    def capabilities(self) -> Any:
        """Deprecated. Use model_info instead."""
        warnings.warn(
            "capabilities is deprecated, use model_info instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._inner_client.capabilities

    def actual_usage(self) -> RequestUsage:
        """Get actual token usage."""
        return self._inner_client.actual_usage()

    def total_usage(self) -> RequestUsage:
        """Get total token usage."""
        return self._inner_client.total_usage()

    def count_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        """Count tokens for the given messages."""
        return self._inner_client.count_tokens(messages, tools=tools)

    def remaining_tokens(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
    ) -> int:
        """Get remaining tokens for the model's context."""
        return self._inner_client.remaining_tokens(messages, tools=tools)

    async def close(self) -> None:
        """Close the client and cancel any pending prewarm tasks."""
        # Cancel any running prewarm tasks
        for task in self._prewarm_tasks:
            if not task.done():
                task.cancel()
        self._prewarm_tasks.clear()

        await self._inner_client.close()

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        """Create a non-streaming response.

        Note: Speculative execution is most effective with streaming.
        This method delegates directly to the inner client.
        """
        return await self._inner_client.create(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        tool_choice: Tool | Literal["auto", "required", "none"] = "auto",
        json_output: Optional[bool | type] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        """Create a streaming response with speculative reasoning execution.

        This is the core method that implements the SRE pattern:
        1. Stream tokens from the inner client
        2. Monitor reasoning content with the sniffer
        3. Fire prewarm tasks when intents are detected (non-blocking)
        4. Continue streaming without interruption

        Yields:
            String chunks during streaming, ending with a CreateResult.
        """
        # Initialize performance metrics
        metrics = PerformanceMetrics()
        metrics.stream_start_time = time.perf_counter()

        # Reset sniffer and triggered intents for fresh session
        self._sniffer.reset()
        self._triggered_intents.clear()

        # Track reasoning state
        is_in_reasoning = False
        reasoning_buffer = ""

        # Get the inner stream
        inner_stream = self._inner_client.create_stream(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )

        async for chunk in inner_stream:
            # Track first token time
            if metrics.first_token_time is None:
                metrics.first_token_time = time.perf_counter()

            # If this is the final CreateResult, process it
            if isinstance(chunk, CreateResult):
                metrics.stream_end_time = time.perf_counter()

                # Log performance summary
                self._last_metrics = metrics
                trace_logger.info(f"SpeculativeClient metrics: {metrics.summary()}")

                # Check if there were tool calls - record timing
                if chunk.content and isinstance(chunk.content, list):
                    metrics.tool_call_time = time.perf_counter()

                yield chunk
                return

            # Process string chunks
            chunk_str = str(chunk)

            # Detect reasoning block boundaries
            if "<think>" in chunk_str:
                is_in_reasoning = True
                metrics.reasoning_start_time = time.perf_counter()

            if "</think>" in chunk_str:
                is_in_reasoning = False
                metrics.reasoning_end_time = time.perf_counter()
                reasoning_buffer = ""

            # Run sniffer on content
            # For distilled models without <think> tags, sniff all content
            # For full R1 models, only sniff inside <think> blocks
            should_sniff = self._enable_speculation and (
                self._sniff_all_content or is_in_reasoning
            )

            if should_sniff:
                reasoning_buffer += chunk_str

                # Sniff for tool intents
                intent = self._sniffer.sniff(chunk_str)

                if intent and intent.confidence >= self._min_confidence:
                    metrics.intents_detected += 1

                    if metrics.first_intent_detected_time is None:
                        metrics.first_intent_detected_time = time.perf_counter()

                    # DEDUPLICATION: Only fire once per tool type per session
                    # Use tool_type as the dedup key (could also include query_hint for finer granularity)
                    dedup_key = intent.tool_type

                    if dedup_key not in self._triggered_intents:
                        self._triggered_intents.add(dedup_key)

                        # Log the prewarm event
                        event = SpeculativePrewarmEvent(
                            tool_type=intent.tool_type,
                            query_hint=intent.query_hint,
                            confidence=intent.confidence,
                            detected_at_ms=intent.detected_at_ms,
                            reasoning_context=intent.reasoning_context,
                        )
                        logger.info(event)

                        # SHARK MOVE: Fire and forget the prewarm task
                        if self._prewarm_callback is not None:
                            task = asyncio.create_task(self._trigger_prewarm(intent))
                            self._prewarm_tasks.append(task)
                            metrics.prewarms_triggered += 1

            yield chunk

    async def _trigger_prewarm(self, intent: ToolIntent) -> None:
        """Trigger speculative tool prewarm in the background.

        This runs as a fire-and-forget task. If the speculation is wrong,
        the result is simply not used. If it's right, the cache will have
        the result ready.
        """
        if self._prewarm_callback is None:
            return

        try:
            trace_logger.debug(
                f"Triggering prewarm for {intent.tool_type}: {intent.query_hint}"
            )

            context = {
                "confidence": intent.confidence,
                "reasoning_context": intent.reasoning_context,
            }

            result = await self._prewarm_callback(
                intent.tool_type,
                intent.query_hint,
                context,
            )

            # Store result in cache
            if result is not None:
                self._cache.store(
                    tool_name=intent.tool_type,
                    args={"query_hint": intent.query_hint},
                    result=result,
                    ttl=30.0,  # 30 second TTL
                )
                trace_logger.info(
                    f"Prewarm complete for {intent.tool_type}, result cached"
                )

        except Exception as e:
            # Speculation failure is silent - don't crash the main stream
            trace_logger.warning(f"Prewarm failed for {intent.tool_type}: {e}")

    @property
    def last_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the performance metrics from the last create_stream call."""
        return self._last_metrics

    @property
    def cache(self) -> SpeculativeCache:
        """Access the speculative cache for inspection or manual operations."""
        return self._cache
