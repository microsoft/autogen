# Logging

AGNext uses Python's built-in [`logging`](https://docs.python.org/3/library/logging.html) module.
The logger names are:

- `agnext` for the main logger.

Example of how to use the logger:

```python
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('agnext')
logger.setLevel(logging.DEBUG)
```
