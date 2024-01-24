import sys
import pytest
from autogen.middleware.code_execution import CodeExecutionMiddleware
from autogen.code_utils import (
    is_docker_running,
    in_docker_container,
)

_code_message_1 = """Execute the following Python code:

```python
print('hello world')
```

Done.
"""

_code_message_1_expected_reply = "exitcode: 0 (execution succeeded)\nCode output: \nhello world\n"


def test_code_execution_no_docker() -> None:
    md = CodeExecutionMiddleware(
        code_execution_config={
            "use_docker": False,
            "work_dir": "/tmp",
        }
    )
    messages = [
        {
            "role": "assistant",
            "content": _code_message_1,
        }
    ]
    reply = md.call(messages)
    assert reply == _code_message_1_expected_reply


@pytest.mark.skipif(
    sys.platform in ["win32"] or (not is_docker_running()) or in_docker_container(),
    reason="docker is not running or in docker container already",
)
def test_code_execution_docker() -> None:
    md = CodeExecutionMiddleware(
        code_execution_config={
            "use_docker": True,
            "work_dir": "/tmp",
        }
    )
    messages = [
        {
            "role": "assistant",
            "content": _code_message_1,
        }
    ]
    reply = md.call(messages)
    assert reply == _code_message_1_expected_reply
