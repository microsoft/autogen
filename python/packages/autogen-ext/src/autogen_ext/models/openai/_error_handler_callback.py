import asyncio
import functools
import inspect
import logging
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Tuple, Type, Union

import openai
from autogen_core.models import CreateResult, RequestUsage

logger = logging.getLogger(__name__)

# We define a type for the error callback function.
# The callback should accept the error and return either:
# - a CreateResult (to let the application proceed), or
# - None (to signal the decorator to re-raise or retry).
ErrorCallback = Callable[[Exception], Optional[CreateResult]]


class TruncatedCreateResult(CreateResult):
    """Result emitted when a streaming call ends prematurely."""

    truncated: bool = True

def handle_openai_exceptions(
    retry_exceptions: Tuple[Type[Exception], ...] = (openai.RateLimitError, openai.APIStatusError),
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    error_callbacks: Optional[Dict[Union[Type[Exception], str], ErrorCallback]] = None,
) -> Callable:
    """
    Decorator to handle OpenAI-related API errors for agent calls.

    Args:
        retry_exceptions: A tuple of exception classes that trigger an automatic retry.
            Defaults to (openai.RateLimitError, openai.APIStatusError).
        max_retries: Maximum number of retry attempts for transient errors.
        backoff_seconds: Base backoff delay (exponential) between retries.
        error_callbacks: A dict that can map either exception classes or substring markers
            (e.g. 'content_filter') to a function that returns either a CreateResult or None.
            If None is returned, the error is re-raised or retried.
    """
    if error_callbacks is None:
        error_callbacks = {}

    def decorator(func: Callable) -> Callable:
        if inspect.isasyncgenfunction(func):
            @functools.wraps(func)
            async def agen_wrapper(*args, **kwargs) -> AsyncGenerator[Any, None]:
                attempts = 0
                last_error: Optional[Exception] = None

                while attempts <= max_retries:
                    try:
                        async for item in func(*args, **kwargs):
                            yield item
                        return

                    except Exception as e:
                        for key, callback in error_callbacks.items():
                            if isinstance(key, type) and isinstance(e, key):
                                maybe_result = callback(e)
                                if maybe_result is not None:
                                    yield maybe_result
                                    return
                                break
                            if isinstance(key, str) and key in str(e):
                                maybe_result = callback(e)
                                if maybe_result is not None:
                                    yield maybe_result
                                    return
                                break

                        if any(isinstance(e, ex) for ex in retry_exceptions):
                            attempts += 1
                            if attempts <= max_retries:
                                sleep_time = backoff_seconds * (2 ** (attempts - 1))
                                logger.warning(
                                    f"Retry {attempts}/{max_retries} after error: {e}\n"
                                    f"Sleeping {sleep_time}s before retry."
                                )
                                await asyncio.sleep(sleep_time)
                                continue

                        last_error = e
                        break

                if last_error:
                    raise last_error
                raise RuntimeError("Reached an unexpected state in error handling.")

            return agen_wrapper

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempts = 0
            last_error: Optional[Exception] = None

            while attempts <= max_retries:
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    # Check if any user-defined callback applies.
                    # - A key in `error_callbacks` can be:
                    #       1) an exception class, or
                    #       2) a string substring to look for in e.__str__()
                    for key, callback in error_callbacks.items():
                        # 1) If the key is an exception type and matches `e` exactly.
                        if isinstance(key, type) and isinstance(e, key):
                            maybe_result = callback(e)
                            if maybe_result is not None:
                                return maybe_result
                            break
                        # 2) If the key is a string and it appears in the error message.
                        if isinstance(key, str) and key in str(e):
                            maybe_result = callback(e)
                            if maybe_result is not None:
                                return maybe_result
                            break

                    if any(isinstance(e, ex) for ex in retry_exceptions):
                        attempts += 1
                        if attempts <= max_retries:
                            sleep_time = backoff_seconds * (2 ** (attempts - 1))
                            logger.warning(
                                f"Retry {attempts}/{max_retries} after error: {e}\n"
                                f"Sleeping {sleep_time}s before retry."
                            )
                            await asyncio.sleep(sleep_time)
                            continue

                    last_error = e
                    break

            if last_error:
                raise last_error
            raise RuntimeError("Reached an unexpected state in error handling.")

        return wrapper
    return decorator

def content_filter_callback(e: Exception) -> CreateResult:
    msg = f"OpenAI content safety blocked the request. Original error: {e}"
    # Return a minimal CreateResult with an explanation, so that the app can keep going.
    return CreateResult(
        finish_reason="content_filter",
        content=msg,
        usage=RequestUsage(prompt_tokens=0, completion_tokens=0),
        cached=False,
    )
