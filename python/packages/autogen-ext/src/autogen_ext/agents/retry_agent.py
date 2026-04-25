"""Retry agent wrapper with exponential backoff, circuit breaker, and fallback support."""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence, Type

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: Optional[tuple[Type[Exception], ...]] = None
    timeout: Optional[float] = None


class CircuitBreakerState(Enum):
    """States for the circuit breaker pattern."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker to prevent repeated calls to a failing service."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN and self._last_failure_time is not None:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioned to HALF_OPEN after %.1fs", elapsed)
        return self._state

    def record_success(self) -> None:
        """Record a successful execution, resetting the breaker."""
        if self._state in (CircuitBreakerState.HALF_OPEN, CircuitBreakerState.CLOSED):
            self._consecutive_failures = 0
            self._state = CircuitBreakerState.CLOSED
            logger.debug("Circuit breaker reset to CLOSED after success")

    def record_failure(self) -> None:
        """Record a failure and potentially trip the breaker."""
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()
        if self._consecutive_failures >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                "Circuit breaker tripped to OPEN after %d consecutive failures",
                self._consecutive_failures,
            )

    def can_execute(self) -> bool:
        """Check whether execution is allowed under the current state."""
        current_state = self.state
        if current_state == CircuitBreakerState.CLOSED:
            return True
        if current_state == CircuitBreakerState.HALF_OPEN:
            return True
        return False


@dataclass
class RetryMetrics:
    """Tracks retry statistics for observability."""

    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retry_delay: float = 0.0
    circuit_breaker_trips: int = 0
    last_error: Optional[Exception] = field(default=None, repr=False)


class RetryAgent:
    """Wraps any agent with retry logic, circuit breaking, and optional fallback.

    Args:
        agent: The inner agent to wrap (duck-typed, must have an ``execute`` method).
        config: Retry configuration controlling backoff and limits.
        fallback_agent: An optional agent invoked when all retries are exhausted.
        circuit_breaker: An optional CircuitBreaker instance for failure isolation.
    """

    def __init__(
        self,
        agent: Any,
        config: Optional[RetryConfig] = None,
        fallback_agent: Any = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._agent = agent
        self._config = config or RetryConfig()
        self._fallback_agent = fallback_agent
        self._circuit_breaker = circuit_breaker
        self._metrics = RetryMetrics()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the wrapped agent with retry logic.

        Raises the last encountered exception when all retries (and the
        optional fallback) are exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self._config.max_retries + 2):  # attempt 1 = first try
            # Circuit breaker gate
            if self._circuit_breaker and not self._circuit_breaker.can_execute():
                self._metrics.circuit_breaker_trips += 1
                logger.warning("Circuit breaker is OPEN – skipping attempt %d", attempt)
                break

            self._metrics.total_attempts += 1

            try:
                result = await self._execute_with_timeout(*args, **kwargs)
                self._metrics.successful_attempts += 1
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return result
            except Exception as exc:
                last_error = exc
                self._metrics.failed_attempts += 1
                self._metrics.last_error = exc

                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()

                if not self._should_retry(exc, attempt):
                    logger.debug("Not retrying after attempt %d: %s", attempt, exc)
                    break

                delay = self._calculate_delay(attempt)
                self._metrics.total_retry_delay += delay
                logger.info(
                    "Attempt %d failed (%s). Retrying in %.2fs …",
                    attempt,
                    type(exc).__name__,
                    delay,
                )
                await asyncio.sleep(delay)

        # All retries exhausted – try fallback
        if self._fallback_agent is not None:
            logger.info("All retries exhausted. Invoking fallback agent.")
            try:
                return await self._fallback_agent.execute(*args, **kwargs)
            except Exception as fallback_exc:
                logger.error("Fallback agent also failed: %s", fallback_exc)
                raise fallback_exc from last_error

        if last_error is not None:
            raise last_error
        raise RuntimeError("RetryAgent finished without a result or error")

    def get_metrics(self) -> RetryMetrics:
        """Return a snapshot of the current retry metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset all tracked metrics."""
        self._metrics = RetryMetrics()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calculate_delay(self, attempt: int) -> float:
        """Return the backoff delay for the given *attempt* number."""
        delay = min(
            self._config.base_delay * (self._config.exponential_base ** (attempt - 1)),
            self._config.max_delay,
        )
        if self._config.jitter:
            delay = delay * random.uniform(0.5, 1.0)
        return delay

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Decide whether *error* on *attempt* is eligible for a retry."""
        if attempt > self._config.max_retries:
            return False
        if self._config.retry_on is not None:
            return isinstance(error, self._config.retry_on)
        return True

    async def _execute_with_timeout(self, *args: Any, **kwargs: Any) -> Any:
        """Run the inner agent's ``execute`` with an optional timeout."""
        coro = self._agent.execute(*args, **kwargs)
        if self._config.timeout is not None:
            try:
                return await asyncio.wait_for(coro, timeout=self._config.timeout)
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError(
                    f"Agent execution timed out after {self._config.timeout}s"
                )
        return await coro


# ------------------------------------------------------------------
# Standalone utility
# ------------------------------------------------------------------


async def retry_with_backoff(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Convenience helper that retries an async callable with backoff.

    ``func`` must be an async function (coroutine function).  The helper
    creates a thin adapter and delegates to :class:`RetryAgent`.
    """

    class _FuncAdapter:
        async def execute(self, *a: Any, **kw: Any) -> Any:
            return await func(*a, **kw)

    agent = RetryAgent(_FuncAdapter(), config=config)
    return await agent.execute(*args, **kwargs)
