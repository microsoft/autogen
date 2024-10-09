import logging

from .events import LLMCallEvent


class LLMUsageTracker(logging.Handler):
    def __init__(self) -> None:
        """Logging handler that tracks the number of tokens used in the prompt and completion.

        Example:

            .. code-block:: python

                from autogen_core.application.logging import LLMUsageTracker, EVENT_LOGGER_NAME

                # Set up the logging configuration to use the custom handler
                logger = logging.getLogger(EVENT_LOGGER_NAME)
                logger.setLevel(logging.INFO)
                llm_usage = LLMUsageTracker()
                logger.handlers = [llm_usage]

                # ...

                print(llm_usage.prompt_tokens)
                print(llm_usage.completion_tokens)

        """
        super().__init__()
        self._prompt_tokens = 0
        self._completion_tokens = 0

    @property
    def tokens(self) -> int:
        return self._prompt_tokens + self._completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens

    def reset(self) -> None:
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the log record. To be used by the logging module."""
        try:
            # Use the StructuredMessage if the message is an instance of it
            if isinstance(record.msg, LLMCallEvent):
                event = record.msg
                self._prompt_tokens += event.prompt_tokens
                self._completion_tokens += event.completion_tokens
        except Exception:
            self.handleError(record)
