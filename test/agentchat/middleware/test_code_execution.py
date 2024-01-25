import sys
from typing import Any, Dict, Literal, Optional, Tuple, Union

import pytest

from autogen.agentchat.middleware.code_execution import CodeExecutionMiddleware
from autogen.code_utils import in_docker_container, is_docker_running

_code_message_1 = """Execute the following Python code:

```python
print('hello world')
```

Done.
"""

_code_message_1_expected_reply = "exitcode: 0 (execution succeeded)\nCode output: \nhello world\n"


_code_execution_configs = [
    (False, False),
    (None, {"use_docker": True}),
    ({}, {"use_docker": True}),
    ({"use_docker": True}, {"use_docker": True}),
    ({"use_docker": False}, {"use_docker": False}),
    ({"use_docker": None}, {"use_docker": True}),
]

CodeConfig = Optional[Union[Dict[str, Any], Literal[False]]]


@pytest.mark.parametrize("param", _code_execution_configs)
def test_use_docker(param: Tuple[CodeConfig, CodeConfig]) -> None:
    code_execution_config, expected_code_execution_config = param
    md = CodeExecutionMiddleware(code_execution_config=code_execution_config)

    assert md._code_execution_config == expected_code_execution_config, code_execution_config


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
