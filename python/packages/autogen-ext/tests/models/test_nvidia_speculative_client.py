# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Unit tests for NVIDIA Speculative Reasoning Execution components.

Tests the ReasoningSniffer, SpeculativeCache, and NvidiaSpeculativeClient
for detecting tool-call intents in LLM reasoning streams and managing
speculative pre-warming of tools.
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import pytest
from autogen_core import CancellationToken
from autogen_core.models import (
    CreateResult,
    RequestUsage,
    UserMessage,
)

from autogen_ext.models.nvidia import (
    NvidiaSpeculativeClient,
    ReasoningSniffer,
    SpeculativeCache,
    ToolIntent,
)


class TestReasoningSniffer:
    """Tests for the ReasoningSniffer component."""

    def test_sniffer_initialization(self) -> None:
        """Test that sniffer initializes with default patterns."""
        sniffer = ReasoningSniffer()
        assert sniffer is not None
        assert len(sniffer.PATTERNS) > 0
        assert "web_search" in sniffer.PATTERNS

    def test_sniffer_detects_web_search_intent(self) -> None:
        """Test detection of web search intent patterns."""
        sniffer = ReasoningSniffer()
        
        intent = sniffer.sniff("I will search for Python documentation")
        
        assert intent is not None
        assert intent.tool_type == "web_search"
        assert "Python documentation" in intent.query_hint
        assert intent.confidence > 0.5

    def test_sniffer_detects_database_query_intent(self) -> None:
        """Test detection of database query intent patterns."""
        sniffer = ReasoningSniffer()
        
        intent = sniffer.sniff("I need to check the database for user records")
        
        assert intent is not None
        assert intent.tool_type == "database_query"

    def test_sniffer_detects_calculate_intent(self) -> None:
        """Test detection of calculation intent patterns."""
        sniffer = ReasoningSniffer()
        
        intent = sniffer.sniff("I will calculate the total revenue")
        
        assert intent is not None
        assert intent.tool_type == "calculate"

    def test_sniffer_returns_none_for_non_matching_text(self) -> None:
        """Test that sniffer returns None when no intent is detected."""
        sniffer = ReasoningSniffer()
        
        intent = sniffer.sniff("The weather is nice today")
        
        assert intent is None

    def test_sniffer_accumulates_context(self) -> None:
        """Test that sniffer accumulates context across chunks."""
        sniffer = ReasoningSniffer()
        
        # Send partial text across chunks
        sniffer.sniff("I will ")
        intent = sniffer.sniff("search for documentation")
        
        assert intent is not None
        assert intent.tool_type == "web_search"

    def test_sniffer_reset_clears_context(self) -> None:
        """Test that reset clears the accumulated context."""
        sniffer = ReasoningSniffer()
        
        sniffer.sniff("I will search for ")
        sniffer.reset()
        intent = sniffer.sniff("documentation")
        
        # Should not match after reset since "I will search for" was cleared
        assert intent is None

    def test_sniffer_custom_pattern(self) -> None:
        """Test adding and using custom patterns."""
        sniffer = ReasoningSniffer()
        
        sniffer.add_pattern(
            "custom_tool",
            r"(?:I will|Let me)\s+run\s+custom\s+analysis\s+on\s+(.+)"
        )
        
        intent = sniffer.sniff("I will run custom analysis on the dataset")
        
        assert intent is not None
        assert intent.tool_type == "custom_tool"


class TestSpeculativeCache:
    """Tests for the SpeculativeCache component."""

    def setup_method(self) -> None:
        """Reset cache singleton before each test."""
        SpeculativeCache.reset_instance()

    def test_cache_singleton_pattern(self) -> None:
        """Test that cache follows singleton pattern."""
        cache1 = SpeculativeCache.get_instance()
        cache2 = SpeculativeCache.get_instance()
        
        assert cache1 is cache2

    def test_cache_reset_instance(self) -> None:
        """Test that reset_instance creates a new singleton."""
        cache1 = SpeculativeCache.get_instance()
        cache1.store("web_search", {"query": "test"}, "value")
        
        SpeculativeCache.reset_instance()
        cache2 = SpeculativeCache.get_instance()
        
        assert cache1 is not cache2
        assert cache2.get("web_search", {"query": "test"}) is None

    def test_cache_store_and_retrieve(self) -> None:
        """Test basic store and retrieve functionality."""
        cache = SpeculativeCache.get_instance()
        
        cache.store("web_search", {"query": "test"}, "test_value")
        result = cache.get("web_search", {"query": "test"})
        
        assert result == "test_value"

    def test_cache_returns_none_for_missing_key(self) -> None:
        """Test that get returns None for missing keys."""
        cache = SpeculativeCache.get_instance()
        
        result = cache.get("nonexistent_tool", {"query": "missing"})
        
        assert result is None

    def test_cache_tracks_hits_and_misses(self) -> None:
        """Test that cache tracks hit and miss statistics."""
        cache = SpeculativeCache.get_instance()
        
        cache.store("web_search", {"query": "test"}, "value")
        cache.get("web_search", {"query": "test"})  # Hit
        cache.get("web_search", {"query": "other"})  # Miss
        
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 1
        assert cache.stats["stores"] == 1

    def test_cache_argument_hashing(self) -> None:
        """Test that cache generates consistent hashes from arguments."""
        cache = SpeculativeCache.get_instance()
        
        # Store two entries with same args - should overwrite
        cache.store("web_search", {"query": "test"}, "result1")
        cache.store("web_search", {"query": "test"}, "result2")  # Overwrites
        cache.store("web_search", {"query": "different"}, "result3")
        
        # Should get latest value for same args
        assert cache.get("web_search", {"query": "test"}) == "result2"
        assert cache.get("web_search", {"query": "different"}) == "result3"

    def test_cache_len(self) -> None:
        """Test that len returns number of cached entries."""
        cache = SpeculativeCache.get_instance()
        
        assert len(cache) == 0
        
        cache.store("tool1", {"arg": "a"}, "value1")
        cache.store("tool2", {"arg": "b"}, "value2")
        
        assert len(cache) == 2


class TestNvidiaSpeculativeClient:
    """Tests for the NvidiaSpeculativeClient wrapper."""

    @pytest.fixture
    def mock_inner_client(self) -> MagicMock:
        """Create a mock inner client for testing."""
        client = MagicMock()
        client.model_info = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "r1",
        }
        client.capabilities = MagicMock()
        client.capabilities.vision = False
        client.capabilities.function_calling = True
        client.capabilities.json_output = True
        
        async def mock_close() -> None:
            pass
        
        client.close = AsyncMock(side_effect=mock_close)
        return client

    def test_client_initialization(self, mock_inner_client: MagicMock) -> None:
        """Test that client initializes correctly."""
        SpeculativeCache.reset_instance()
        
        client = NvidiaSpeculativeClient(inner_client=mock_inner_client)
        
        assert client is not None
        assert client._inner_client is mock_inner_client
        assert client._enable_speculation is True

    def test_client_initialization_with_custom_sniffer(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test initialization with custom sniffer."""
        SpeculativeCache.reset_instance()
        custom_sniffer = ReasoningSniffer()
        
        client = NvidiaSpeculativeClient(
            inner_client=mock_inner_client,
            sniffer=custom_sniffer,
        )
        
        assert client._sniffer is custom_sniffer

    def test_client_initialization_with_speculation_disabled(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that speculation can be disabled."""
        SpeculativeCache.reset_instance()
        
        client = NvidiaSpeculativeClient(
            inner_client=mock_inner_client,
            enable_speculation=False,
        )
        
        assert client._enable_speculation is False

    def test_client_exposes_cache(self, mock_inner_client: MagicMock) -> None:
        """Test that cache is accessible via property."""
        SpeculativeCache.reset_instance()
        
        client = NvidiaSpeculativeClient(inner_client=mock_inner_client)
        
        assert client.cache is not None
        assert isinstance(client.cache, SpeculativeCache)

    @pytest.mark.asyncio
    async def test_client_create_delegates_to_inner(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that create() delegates to inner client."""
        SpeculativeCache.reset_instance()
        
        expected_result = CreateResult(
            content="Test response",
            usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
            cached=False,
        )
        mock_inner_client.create = AsyncMock(return_value=expected_result)
        
        client = NvidiaSpeculativeClient(inner_client=mock_inner_client)
        
        result = await client.create(
            messages=[UserMessage(content="Hello", source="user")]
        )
        
        assert result == expected_result
        mock_inner_client.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_close_closes_inner_client(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that close() closes the inner client."""
        SpeculativeCache.reset_instance()
        
        client = NvidiaSpeculativeClient(inner_client=mock_inner_client)
        
        await client.close()
        
        mock_inner_client.close.assert_called_once()


class TestNvidiaSpeculativeClientStreaming:
    """Tests for streaming functionality of NvidiaSpeculativeClient."""

    @pytest.fixture
    def mock_inner_client(self) -> MagicMock:
        """Create a mock inner client with streaming support."""
        client = MagicMock()
        client.model_info = {
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "r1",
        }
        
        async def mock_close() -> None:
            pass
        
        client.close = AsyncMock(side_effect=mock_close)
        return client

    @pytest.mark.asyncio
    async def test_stream_yields_chunks_and_final_result(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that create_stream yields chunks and final CreateResult."""
        SpeculativeCache.reset_instance()
        
        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            yield "Hello"
            yield " World"
            yield CreateResult(
                content="Hello World",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                finish_reason="stop",
                cached=False,
            )
        
        mock_inner_client.create_stream = mock_stream
        
        client = NvidiaSpeculativeClient(inner_client=mock_inner_client)
        
        chunks: List[Any] = []
        async for chunk in client.create_stream(
            messages=[UserMessage(content="Hi", source="user")]
        ):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0] == "Hello"
        assert chunks[1] == " World"
        assert isinstance(chunks[2], CreateResult)

    @pytest.mark.asyncio
    async def test_stream_triggers_prewarm_on_intent_detection(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that prewarm callback is triggered when intent is detected."""
        SpeculativeCache.reset_instance()
        
        prewarm_called = False
        prewarm_tool_type: Optional[str] = None
        
        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            nonlocal prewarm_called, prewarm_tool_type
            prewarm_called = True
            prewarm_tool_type = tool_type
            return "mock_result"
        
        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            # Simulate reasoning content with tool intent
            yield "<think>"
            yield "I will search for Python documentation"
            yield "</think>"
            yield CreateResult(
                content="Here's the documentation",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=20),
                finish_reason="stop",
                cached=False,
            )
        
        mock_inner_client.create_stream = mock_stream
        
        client = NvidiaSpeculativeClient(
            inner_client=mock_inner_client,
            prewarm_callback=prewarm_callback,
            min_confidence=0.5,
        )
        
        chunks: List[Any] = []
        async for chunk in client.create_stream(
            messages=[UserMessage(content="Find docs", source="user")]
        ):
            chunks.append(chunk)
        
        # Allow background tasks to complete
        await asyncio.sleep(0.2)
        
        assert prewarm_called is True
        assert prewarm_tool_type == "web_search"

    @pytest.mark.asyncio
    async def test_stream_respects_min_confidence(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that prewarm is only triggered above min_confidence."""
        SpeculativeCache.reset_instance()
        
        prewarm_called = False
        
        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            nonlocal prewarm_called
            prewarm_called = True
            return None
        
        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            yield "Maybe I should search"  # Low confidence phrase
            yield CreateResult(
                content="Done",
                usage=RequestUsage(prompt_tokens=5, completion_tokens=2),
                finish_reason="stop",
                cached=False,
            )
        
        mock_inner_client.create_stream = mock_stream
        
        client = NvidiaSpeculativeClient(
            inner_client=mock_inner_client,
            prewarm_callback=prewarm_callback,
            min_confidence=0.99,  # Very high threshold
        )
        
        async for _ in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            pass
        
        await asyncio.sleep(0.1)
        
        # Should not trigger because confidence is below threshold
        assert prewarm_called is False

    @pytest.mark.asyncio
    async def test_stream_deduplicates_intents(
        self, mock_inner_client: MagicMock
    ) -> None:
        """Test that same intent is only fired once per session."""
        SpeculativeCache.reset_instance()
        
        prewarm_count = 0
        
        async def prewarm_callback(
            tool_type: str, query_hint: str, context: Dict[str, Any]
        ) -> Optional[str]:
            nonlocal prewarm_count
            prewarm_count += 1
            return "result"
        
        async def mock_stream(
            messages: Any, **kwargs: Any
        ) -> AsyncGenerator[Union[str, CreateResult], None]:
            # Multiple search intents in same stream
            yield "I will search for Python docs. "
            yield "Let me search for more info. "
            yield "I need to search again. "
            yield CreateResult(
                content="Done",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                finish_reason="stop",
                cached=False,
            )
        
        mock_inner_client.create_stream = mock_stream
        
        client = NvidiaSpeculativeClient(
            inner_client=mock_inner_client,
            prewarm_callback=prewarm_callback,
            min_confidence=0.5,
            sniff_all_content=True,
        )
        
        async for _ in client.create_stream(
            messages=[UserMessage(content="Test", source="user")]
        ):
            pass
        
        await asyncio.sleep(0.2)
        
        # Should only fire once due to deduplication
        assert prewarm_count == 1
