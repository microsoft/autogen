import logging
import time
import os
from autogen_core.logging import LLMCallEvent

class LLMUsageTracker(logging.Handler):
    def __init__(self) -> None:
        """Logging handler that tracks the number of tokens used in the prompt and completion."""
        super().__init__()
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_cost = 0.0

    @property
    def total_tokens(self) -> int:
        return self._prompt_tokens + self._completion_tokens

    @property
    def prompt_tokens(self) -> int:
        return self._prompt_tokens

    @property
    def completion_tokens(self) -> int:
        return self._completion_tokens

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def reset(self) -> None:
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._total_cost = 0.0

    def emit(self, record: logging.LogRecord) -> None:
        """Emit the log record. To be used by the logging module."""
        try:
            # Use the StructuredMessage if the message is an instance of it
            if isinstance(record.msg, LLMCallEvent):
                event = record.msg
                self._prompt_tokens += event.prompt_tokens
                self._completion_tokens += event.completion_tokens
                self._total_cost += event.cost
        except Exception:
            self.handleError(record)

def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "runtime.log")),
            logging.StreamHandler(),
        ],
    )

def log_llm_io(agent_name, prompt, reasoning, output):
    log_dir = "logs/llm_io"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = time.strftime("%Y%m%d-%H%M%S")

    with open(os.path.join(log_dir, f"{agent_name}_{timestamp}_prompt.txt"), "w") as f:
        f.write(prompt)

    with open(os.path.join(log_dir, f"{agent_name}_{timestamp}_reasoning.txt"), "w") as f:
        f.write(str(reasoning))

    with open(os.path.join(log_dir, f"{agent_name}_{timestamp}_output.txt"), "w") as f:
        f.write(str(output))

def log_wrapper(reply_func):
    def wrapper(recipient, messages, sender, config):
        # Log the received message
        if messages is not None and len(messages) > 0:
            log_llm_io(
                recipient.name,
                messages[-1].get("content", ""),
                "",  # No reasoning available here
                "",  # No output available yet
            )

        # Call the original reply function
        reply = reply_func(recipient, messages, sender, config)

        # Log the generated reply
        if reply is not None:
            log_llm_io(
                recipient.name,
                "",  # No prompt available here
                "",  # No reasoning available here
                reply.get("content", ""),
            )
        return reply
    return wrapper
