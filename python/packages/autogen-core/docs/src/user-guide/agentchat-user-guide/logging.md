# Logging

AutoGen uses Python's built-in [`logging`](https://docs.python.org/3/library/logging.html) module.

To enable logging for AgentChat, you can use the following code:

```python
import logging

from autogen_agentchat import EVENT_LOGGER_NAME, TRACE_LOGGER_NAME

logging.basicConfig(level=logging.WARNING)

# For trace logging.
trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.addHandler(logging.StreamHandler())
trace_logger.setLevel(logging.DEBUG)

# For structured message logging, such as low-level messages between agents.
event_logger = logging.getLogger(EVENT_LOGGER_NAME)
event_logger.addHandler(logging.StreamHandler())
event_logger.setLevel(logging.DEBUG)
```

To enable additional logs such as model client calls and agent runtime events,
please refer to the [Core Logging Guide](../core-user-guide/framework/logging.md).