import time

import pytest

from autogen.oai.rate_limiters import TimeRateLimiter


@pytest.mark.parametrize("execute_n_times", range(5))
def test_time_rate_limiter(execute_n_times):
    current_time_seconds = time.time()

    rate = 1
    rate_limiter = TimeRateLimiter(rate)

    n_loops = 2
    for _ in range(n_loops):
        rate_limiter.sleep()

    total_time = time.time() - current_time_seconds
    min_expected_time = (n_loops - 1) / rate
    assert total_time >= min_expected_time
