"""Tests for LLMCallEvent and LLMStreamEndEvent timing fields.

These tests verify the performance telemetry fields added in Issue #5790.
"""

import json

from autogen_core.logging import LLMCallEvent, LLMStreamEndEvent


def test_llm_call_event_timing_fields() -> None:
    """Test that LLMCallEvent correctly stores and serializes timing fields."""
    event = LLMCallEvent(
        messages=[{"role": "user", "content": "Hello"}],
        response={"content": "Hi there!"},
        prompt_tokens=10,
        completion_tokens=20,
        latency_ms=150.5,
        tokens_per_second=133.33,
    )

    # Check property accessors
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 20
    assert event.latency_ms == 150.5
    assert event.tokens_per_second == 133.33

    # Check JSON serialization includes timing fields
    json_str = str(event)
    data = json.loads(json_str)
    assert data["latency_ms"] == 150.5
    assert data["tokens_per_second"] == 133.33


def test_llm_call_event_timing_fields_optional() -> None:
    """Test that timing fields are optional and not included when not provided."""
    event = LLMCallEvent(
        messages=[{"role": "user", "content": "Hello"}],
        response={"content": "Hi there!"},
        prompt_tokens=10,
        completion_tokens=20,
    )

    # Check that missing fields return None
    assert event.latency_ms is None
    assert event.tokens_per_second is None

    # Check JSON serialization excludes missing timing fields
    json_str = str(event)
    data = json.loads(json_str)
    assert "latency_ms" not in data
    assert "tokens_per_second" not in data


def test_llm_stream_end_event_timing_fields() -> None:
    """Test that LLMStreamEndEvent correctly stores and serializes timing fields including TTFT."""
    event = LLMStreamEndEvent(
        response={"content": "Hello, world!"},
        prompt_tokens=10,
        completion_tokens=25,
        latency_ms=200.0,
        tokens_per_second=125.0,
        ttft_ms=50.5,
    )

    # Check property accessors
    assert event.prompt_tokens == 10
    assert event.completion_tokens == 25
    assert event.latency_ms == 200.0
    assert event.tokens_per_second == 125.0
    assert event.ttft_ms == 50.5

    # Check JSON serialization includes all timing fields
    json_str = str(event)
    data = json.loads(json_str)
    assert data["latency_ms"] == 200.0
    assert data["tokens_per_second"] == 125.0
    assert data["ttft_ms"] == 50.5


def test_llm_stream_end_event_timing_fields_optional() -> None:
    """Test that streaming timing fields are optional."""
    event = LLMStreamEndEvent(
        response={"content": "Hello, world!"},
        prompt_tokens=10,
        completion_tokens=25,
    )

    # Check that missing fields return None
    assert event.latency_ms is None
    assert event.tokens_per_second is None
    assert event.ttft_ms is None

    # Check JSON serialization excludes missing timing fields
    json_str = str(event)
    data = json.loads(json_str)
    assert "latency_ms" not in data
    assert "tokens_per_second" not in data
    assert "ttft_ms" not in data


if __name__ == "__main__":
    test_llm_call_event_timing_fields()
    test_llm_call_event_timing_fields_optional()
    test_llm_stream_end_event_timing_fields()
    test_llm_stream_end_event_timing_fields_optional()
    print("All tests passed!")
