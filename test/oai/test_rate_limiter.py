import pytest
import time
from autogen.oai.rate_limiter import TimeRateLimiter


def test_time_rate_limiter():
    current_time_seconds = time.perf_counter()

    rate = 1
    rate_limiter = TimeRateLimiter(rate)

    n_loops = 2
    for _ in range(n_loops):
        rate_limiter.wait()

    total_time = time.perf_counter() - current_time_seconds
    min_expected_time = (n_loops - 1) / rate
    assert total_time >= min_expected_time


@pytest.mark.asyncio
async def test_a_time_rate_limiter():
    current_time_seconds = time.perf_counter()

    rate = 1
    rate_limiter = TimeRateLimiter(rate)

    n_loops = 2
    for _ in range(n_loops):
        await rate_limiter.a_wait()

    total_time = time.perf_counter() - current_time_seconds
    min_expected_time = (n_loops - 1) / rate
    assert total_time >= min_expected_time
