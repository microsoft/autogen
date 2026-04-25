"""Tests for RetryAgent with exponential backoff, circuit breaker, and fallback."""

import asyncio

import pytest

from autogen_ext.agents.retry_agent import (
    CircuitBreaker,
    CircuitBreakerState,
    RetryAgent,
    RetryConfig,
    RetryMetrics,
    retry_with_backoff,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockAgent:
    """Simple agent that succeeds on every call."""

    def __init__(self, return_value: str = "ok") -> None:
        self._return_value = return_value
        self.call_count = 0

    async def execute(self, *args, **kwargs):
        self.call_count += 1
        return self._return_value


class FailNTimesAgent:
    """Agent that raises for the first *n* calls, then succeeds."""

    def __init__(self, fail_count: int, exception: Exception | None = None) -> None:
        self._fail_count = fail_count
        self._exception = exception or RuntimeError("transient failure")
        self.call_count = 0

    async def execute(self, *args, **kwargs):
        self.call_count += 1
        if self.call_count <= self._fail_count:
            raise self._exception
        return "recovered"


class AlwaysFailAgent:
    """Agent that always raises."""

    def __init__(self, exception: Exception | None = None) -> None:
        self._exception = exception or RuntimeError("permanent failure")
        self.call_count = 0

    async def execute(self, *args, **kwargs):
        self.call_count += 1
        raise self._exception


class SlowAgent:
    """Agent that sleeps longer than expected."""

    def __init__(self, delay: float = 5.0) -> None:
        self._delay = delay

    async def execute(self, *args, **kwargs):
        await asyncio.sleep(self._delay)
        return "slow_ok"


# ---------------------------------------------------------------------------
# Tests – basic execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_execution_no_retries():
    agent = MockAgent(return_value="hello")
    wrapper = RetryAgent(agent, RetryConfig(max_retries=3))

    result = await wrapper.execute()

    assert result == "hello"
    assert agent.call_count == 1
    metrics = wrapper.get_metrics()
    assert metrics.total_attempts == 1
    assert metrics.successful_attempts == 1
    assert metrics.failed_attempts == 0


@pytest.mark.asyncio
async def test_retry_on_transient_failure():
    agent = FailNTimesAgent(fail_count=2)
    config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(agent, config)

    result = await wrapper.execute()

    assert result == "recovered"
    assert agent.call_count == 3
    metrics = wrapper.get_metrics()
    assert metrics.successful_attempts == 1
    assert metrics.failed_attempts == 2


@pytest.mark.asyncio
async def test_max_retries_exceeded():
    agent = AlwaysFailAgent()
    config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(agent, config)

    with pytest.raises(RuntimeError, match="permanent failure"):
        await wrapper.execute()

    assert agent.call_count == 3  # 1 initial + 2 retries
    metrics = wrapper.get_metrics()
    assert metrics.failed_attempts == 3
    assert metrics.successful_attempts == 0


# ---------------------------------------------------------------------------
# Tests – backoff timing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exponential_backoff_delays():
    config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
    wrapper = RetryAgent(MockAgent(), config)

    assert wrapper._calculate_delay(1) == pytest.approx(1.0)
    assert wrapper._calculate_delay(2) == pytest.approx(2.0)
    assert wrapper._calculate_delay(3) == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_max_delay_cap():
    config = RetryConfig(base_delay=10.0, max_delay=15.0, exponential_base=2.0, jitter=False)
    wrapper = RetryAgent(MockAgent(), config)

    assert wrapper._calculate_delay(5) == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_jitter_randomisation():
    config = RetryConfig(base_delay=2.0, jitter=True)
    wrapper = RetryAgent(MockAgent(), config)

    delays = [wrapper._calculate_delay(1) for _ in range(50)]
    assert all(1.0 <= d <= 2.0 for d in delays)
    assert len(set(delays)) > 1  # not all identical


# ---------------------------------------------------------------------------
# Tests – circuit breaker
# ---------------------------------------------------------------------------

def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(failure_threshold=3)
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_trips_on_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_resets_on_success():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_half_open_after_recovery(monkeypatch):
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    # Fast-forward time past the recovery timeout
    import time as _time

    original_last = cb._last_failure_time
    monkeypatch.setattr(cb, "_last_failure_time", original_last - 2.0)
    assert cb.state == CircuitBreakerState.HALF_OPEN
    assert cb.can_execute() is True


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_execution():
    cb = CircuitBreaker(failure_threshold=1)
    cb.record_failure()  # trips immediately

    agent = MockAgent()
    config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(agent, config, circuit_breaker=cb)

    with pytest.raises(RuntimeError, match="without a result"):
        await wrapper.execute()

    assert agent.call_count == 0
    assert wrapper.get_metrics().circuit_breaker_trips >= 1


# ---------------------------------------------------------------------------
# Tests – fallback agent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fallback_agent_activation():
    primary = AlwaysFailAgent()
    fallback = MockAgent(return_value="fallback_result")
    config = RetryConfig(max_retries=1, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(primary, config, fallback_agent=fallback)

    result = await wrapper.execute()

    assert result == "fallback_result"
    assert primary.call_count == 2  # 1 initial + 1 retry
    assert fallback.call_count == 1


@pytest.mark.asyncio
async def test_fallback_agent_also_fails():
    primary = AlwaysFailAgent(RuntimeError("primary"))
    fallback = AlwaysFailAgent(ValueError("fallback"))
    config = RetryConfig(max_retries=0, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(primary, config, fallback_agent=fallback)

    with pytest.raises(ValueError, match="fallback"):
        await wrapper.execute()


# ---------------------------------------------------------------------------
# Tests – timeout handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_raises_on_slow_agent():
    agent = SlowAgent(delay=5.0)
    config = RetryConfig(max_retries=0, timeout=0.05)
    wrapper = RetryAgent(agent, config)

    with pytest.raises(asyncio.TimeoutError):
        await wrapper.execute()


@pytest.mark.asyncio
async def test_timeout_retries_then_fails():
    agent = SlowAgent(delay=5.0)
    config = RetryConfig(max_retries=2, timeout=0.05, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(agent, config)

    with pytest.raises(asyncio.TimeoutError):
        await wrapper.execute()

    assert wrapper.get_metrics().failed_attempts == 3


# ---------------------------------------------------------------------------
# Tests – selective retry_on
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_on_filters_exception_types():
    agent = AlwaysFailAgent(ValueError("not retryable"))
    config = RetryConfig(max_retries=3, base_delay=0.01, retry_on=(RuntimeError,))
    wrapper = RetryAgent(agent, config)

    with pytest.raises(ValueError, match="not retryable"):
        await wrapper.execute()

    assert agent.call_count == 1  # no retries for ValueError


# ---------------------------------------------------------------------------
# Tests – metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_tracking():
    agent = FailNTimesAgent(fail_count=1)
    config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
    wrapper = RetryAgent(agent, config)

    await wrapper.execute()
    m = wrapper.get_metrics()

    assert m.total_attempts == 2
    assert m.successful_attempts == 1
    assert m.failed_attempts == 1
    assert m.total_retry_delay > 0


@pytest.mark.asyncio
async def test_reset_metrics():
    agent = MockAgent()
    wrapper = RetryAgent(agent, RetryConfig())

    await wrapper.execute()
    wrapper.reset_metrics()
    m = wrapper.get_metrics()

    assert m.total_attempts == 0
    assert m.successful_attempts == 0


# ---------------------------------------------------------------------------
# Tests – standalone utility
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_with_backoff_utility():
    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("not yet")
        return "done"

    config = RetryConfig(max_retries=5, base_delay=0.01, jitter=False)
    result = await retry_with_backoff(flaky_func, config)

    assert result == "done"
    assert call_count == 3
