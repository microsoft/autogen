import logging

from autogen_core.application.logging import EVENT_LOGGER_NAME, LLMUsageTracker
from autogen_core.application.logging.events import LLMCallEvent


def test_llm_usage() -> None:
    # Set up the logging configuration to use the custom handler
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    llm_usage = LLMUsageTracker()
    logger.handlers = [llm_usage]

    logger.info(LLMCallEvent(prompt_tokens=10, completion_tokens=20))

    assert llm_usage.prompt_tokens == 10
    assert llm_usage.completion_tokens == 20

    logger.info(LLMCallEvent(prompt_tokens=1, completion_tokens=1))

    assert llm_usage.prompt_tokens == 11
    assert llm_usage.completion_tokens == 21

    llm_usage.reset()

    assert llm_usage.prompt_tokens == 0
    assert llm_usage.completion_tokens == 0

    logger.info(LLMCallEvent(prompt_tokens=1, completion_tokens=1))

    assert llm_usage.prompt_tokens == 1
    assert llm_usage.completion_tokens == 1
