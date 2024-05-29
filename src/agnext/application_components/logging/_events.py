import json
from typing import Any, cast


class LLMCallEvent:
    def __init__(self, *, prompt_tokens: int, completion_tokens: int, **kwargs: Any) -> None:
        """To be used by model clients to log the call to the LLM.

        Args:
            prompt_tokens (int): Number of tokens used in the prompt.
            completion_tokens (int): Number of tokens used in the completion.

        Example:

            .. code-block:: python

                from agnext.application_components.logging import LLMCallEvent, EVENT_LOGGER_NAME

                logger = logging.getLogger(EVENT_LOGGER_NAME)
                logger.info(LLMCallEvent(prompt_tokens=10, completion_tokens=20))

        """
        self.kwargs = kwargs
        self.kwargs["prompt_tokens"] = prompt_tokens
        self.kwargs["completion_tokens"] = completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return cast(int, self.kwargs["prompt_tokens"])

    @property
    def completion_tokens(self) -> int:
        return cast(int, self.kwargs["completion_tokens"])

    # This must output the event in a json serializable format
    def __str__(self) -> str:
        return json.dumps(self.kwargs)
