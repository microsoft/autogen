# Logging

AGNext uses Python's built-in [`logging`](https://docs.python.org/3/library/logging.html) module.

There are two kinds of logging:

- **Trace logging**: This is used for debugging and is human readable messages to indicate what is going on. This is intended for a developer to understand what is happening in the code. The content and format of these logs should not be depended on by other systems.
    - Name: {py:attr}`~autogen_core.application.logging.TRACE_LOGGER_NAME`.
- **Structured logging**: This logger emits structured events that can be consumed by other systems. The content and format of these logs should be can be depended on by other systems.
    - Name: {py:attr}`~autogen_core.application.logging.EVENT_LOGGER_NAME`.
    - See the module {py:mod}`autogen_core.application.logging.events` to see the available events.
- {py:attr}`~autogen_core.application.logging.ROOT_LOGGER` can be used to enable or disable all logs at the same time.

## Enabling logging output

To enable trace logging, you can use the following code:

```python
import logging

from autogen_core.application.logging import TRACE_LOGGER_NAME

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(TRACE_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
```

### Structured logging

Structured logging allows you to write handling logic that deals with the actual events including all fields rather than just a formatted string.

For example, if you had defined this custom event and were emitting it. Then you could write the following handler to receive it.

```python
import logging
from dataclasses import dataclass

@dataclass
class MyEvent:
    timestamp: str
    message: str

class MyHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Use the StructuredMessage if the message is an instance of it
            if isinstance(record.msg, MyEvent):
                print(f"Timestamp: {record.msg.timestamp}, Message: {record.msg.message}")
        except Exception:
            self.handleError(record)
```

And this is how you could use it:

```python
logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.INFO)
my_handler = MyHandler()
logger.handlers = [my_handler]
```


## Emitting logs

These two names are the root loggers for these types. Code that emits logs should use a child logger of these loggers. For example, if you are writing a module `my_module` and you want to emit trace logs, you should use the logger named:

```python
import logging

from autogen_core.application.logging import TRACE_LOGGER_NAME
logger = logging.getLogger(f"{TRACE_LOGGER_NAME}.my_module")
```

### Emitting structured logs

If your event looks like:

```python
from dataclasses import dataclass

@dataclass
class MyEvent:
    timestamp: str
    message: str
```

Then it could be emitted in code like this:

```python
from autogen_core.application.logging import EVENT_LOGGER_NAME

logger = logging.getLogger(EVENT_LOGGER_NAME + ".my_module")
logger.info(MyEvent("timestamp", "message"))
```
