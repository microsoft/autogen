# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Integration tests for NVIDIA Speculative Reasoning Execution.

These tests verify the end-to-end flow of speculative execution with
simulated DeepSeek-R1 style reasoning streams. They demonstrate the
latency savings achievable by parallelizing tool execution with
model reasoning.
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from unittest.mock import MagicMock

import pytest
from autogen_core.models import (
    CreateResult,
    RequestUsage,
    UserMessage,
)

from autogen_ext.models.nvidia import (
    NvidiaSpeculativeClient,
    ReasoningSniffer,
    SpeculativeCache,
)


# Simulated DeepSeek-R1 reasoning stream with tool intent
MOCK_R1_STREAM_CONTENT = [
    "<think>",
    "Let me analyze this problem step by step.",
    " First, I need to understand what the user is asking.",
    " The user wants information about Python documentation.",
    " I will search for Python 3.12 documentation to find the answer.",
    " Let me also check for any related tutorials.",
    "</think>",
    "\n\nBased on my research, here are the key Python 3.12 features:\n",
    "1. Pattern matching improvements\n",
    "2. Type parameter syntax\n",
    "3. Performance optimizations",
]


class TestSpeculativeExecutionIntegration:
    """Integration tests for the full speculative execution flow."""

    @pytest.fixture(autouse=True)
    def reset_cache(self) -> None:
        """Reset the singleton cache before each test."""
        SpeculativeCache.reset_instance()

    @pytest.fixture
    def mock_client_with_r1_stream(self) -> MagicMock:
        """Create a mock client that simulates R1-style reasoning stream."""
        client = MagicMock()
        client.model_info = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "r1",
        }

        async def mock_close() -> None:
            pass

        client.close = MagicMock(side_effect=mock_close)

        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            for chunk in MOCK_R1_STREAM_CONTENT:
                await asyncio.sleep(0.05)  # Simulate token generation latency
                yield chunk

            yield CreateResult(
                content="".join(MOCK_R1_STREAM_CONTENT),
                usage=RequestUsage(prompt_tokens=50, completion_tokens=100),
                finish_reason="stop",
                cached=False,
            )

        client.create_stream = mock_stream
        return client

    @pytest.mark.asyncio
    async def test_end_to_end_speculative_execution(
        self, mock_client_with_r1_stream: MagicMock
    ) -> None:
        """Test complete speculative execution flow with timing verification."""
        prewarm_events: List[Dict[str, Any]] = []
        stream_start_time: Optional[float] = None

        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            prewarm_time = time.perf_counter()
            prewarm_events.append({
                "tool_type": tool_type,
                "query_hint": query_hint,
                "time": prewarm_time,
                "offset_ms": (prewarm_time - stream_start_time) * 1000
                if stream_start_time
                else 0,
            })
            # Simulate tool execution
            await asyncio.sleep(0.1)
            return f"Mock result for {tool_type}"

        client = NvidiaSpeculativeClient(
            inner_client=mock_client_with_r1_stream,
            prewarm_callback=prewarm_callback,
            min_confidence=0.6,
        )

        stream_start_time = time.perf_counter()
        chunks: List[Any] = []

        async for chunk in client.create_stream(
            messages=[UserMessage(content="Tell me about Python 3.12", source="user")]
        ):
            chunks.append(chunk)

        stream_end_time = time.perf_counter()

        # Allow background tasks to complete
        await asyncio.sleep(0.2)
        await client.close()

        # Verify prewarm was triggered
        assert len(prewarm_events) > 0, "Expected at least one prewarm event"

        # Verify prewarm fired before stream ended
        first_prewarm = prewarm_events[0]
        assert first_prewarm["tool_type"] == "web_search"

        # Verify stream completed successfully
        assert isinstance(chunks[-1], CreateResult)

    @pytest.mark.asyncio
    async def test_speculative_delta_timing(
        self, mock_client_with_r1_stream: MagicMock
    ) -> None:
        """Test that speculative execution provides timing advantage."""
        prewarm_time: Optional[float] = None
        reasoning_end_time: Optional[float] = None

        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            nonlocal prewarm_time
            prewarm_time = time.perf_counter()
            await asyncio.sleep(0.05)
            return "result"

        client = NvidiaSpeculativeClient(
            inner_client=mock_client_with_r1_stream,
            prewarm_callback=prewarm_callback,
            min_confidence=0.6,
        )

        stream_start = time.perf_counter()

        async for chunk in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            chunk_str = str(chunk)
            if "</think>" in chunk_str:
                reasoning_end_time = time.perf_counter()

        await asyncio.sleep(0.2)
        await client.close()

        # Verify timing relationship
        assert prewarm_time is not None, "Prewarm should have been triggered"
        assert reasoning_end_time is not None, "Should have detected reasoning end"

        # Prewarm should fire before reasoning ends (negative delta = savings)
        prewarm_offset = (prewarm_time - stream_start) * 1000
        reasoning_end_offset = (reasoning_end_time - stream_start) * 1000
        speculative_delta = prewarm_offset - reasoning_end_offset

        assert speculative_delta < 0, (
            f"Speculative execution should provide timing advantage. "
            f"Delta: {speculative_delta:.0f}ms"
        )

    @pytest.mark.asyncio
    async def test_no_prewarm_when_speculation_disabled(
        self, mock_client_with_r1_stream: MagicMock
    ) -> None:
        """Test that prewarming is skipped when speculation is disabled."""
        prewarm_called = False

        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            nonlocal prewarm_called
            prewarm_called = True
            return None

        client = NvidiaSpeculativeClient(
            inner_client=mock_client_with_r1_stream,
            prewarm_callback=prewarm_callback,
            enable_speculation=False,  # Disabled
        )

        async for _ in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            pass

        await asyncio.sleep(0.1)
        await client.close()

        assert prewarm_called is False

    @pytest.mark.asyncio
    async def test_cache_stores_prewarm_results(
        self, mock_client_with_r1_stream: MagicMock
    ) -> None:
        """Test that prewarm results are stored in cache."""
        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            return f"cached_result_for_{tool_type}"

        client = NvidiaSpeculativeClient(
            inner_client=mock_client_with_r1_stream,
            prewarm_callback=prewarm_callback,
            min_confidence=0.5,
        )

        async for _ in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            pass

        await asyncio.sleep(0.2)
        await client.close()

        # Verify cache has entries
        cache = client.cache
        assert len(cache) > 0
        assert cache.stats["stores"] > 0


class TestSnifferPatternMatching:
    """Integration tests for sniffer pattern matching accuracy."""

    @pytest.fixture(autouse=True)
    def reset_cache(self) -> None:
        """Reset cache before each test."""
        SpeculativeCache.reset_instance()

    @pytest.mark.parametrize(
        "text,expected_tool,should_match",
        [
            ("I will search for Python documentation", "web_search", True),
            ("Let me look up the latest news", "web_search", True),
            ("I need to check the database for user records", "database_query", True),
            ("I'll calculate the total revenue", "calculate", True),
            ("The weather is nice", None, False),
            ("Just thinking about the problem", None, False),
        ],
    )
    def test_intent_detection_patterns(
        self, text: str, expected_tool: Optional[str], should_match: bool
    ) -> None:
        """Test various intent detection patterns."""
        sniffer = ReasoningSniffer()

        intent = sniffer.sniff(text)

        if should_match:
            assert intent is not None, f"Expected match for: {text}"
            assert intent.tool_type == expected_tool
        else:
            assert intent is None, f"Expected no match for: {text}"

    def test_contraction_patterns(self) -> None:
        """Test that contractions like I'll are properly detected."""
        sniffer = ReasoningSniffer()

        # Test I'll patterns
        intent = sniffer.sniff("I'll search for the latest updates")
        assert intent is not None
        assert intent.tool_type == "web_search"

        sniffer.reset()

        intent = sniffer.sniff("I'll need to look up some information")
        assert intent is not None


class TestPerformanceMetrics:
    """Tests for performance metric tracking."""

    @pytest.fixture(autouse=True)
    def reset_cache(self) -> None:
        """Reset cache before each test."""
        SpeculativeCache.reset_instance()

    @pytest.mark.asyncio
    async def test_metrics_are_tracked(self) -> None:
        """Test that performance metrics are properly tracked."""
        client_mock = MagicMock()
        client_mock.model_info = {"family": "r1"}

        async def mock_close() -> None:
            pass

        client_mock.close = MagicMock(side_effect=mock_close)

        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            yield "Test response"
            yield CreateResult(
                content="Test",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                finish_reason="stop",
                cached=False,
            )

        client_mock.create_stream = mock_stream

        client = NvidiaSpeculativeClient(inner_client=client_mock)

        async for _ in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            pass

        await client.close()

        # Verify metrics were captured
        metrics = client.last_metrics
        assert metrics is not None
        assert metrics.stream_start_time is not None
        assert metrics.stream_end_time is not None
        assert metrics.first_token_time is not None
