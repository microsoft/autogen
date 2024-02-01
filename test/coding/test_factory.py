from typing import Dict, Union
import pytest
from autogen.coding.base import CodeExecutor
from autogen.coding.commandline_code_executor import CommandlineCodeExecutor
from autogen.coding.factory import CodeExecutorFactory
from autogen.coding.embedded_ipython_code_executor import EmbeddedIPythonCodeExecutor


def test_create() -> None:
    config: Dict[str, Union[str, CodeExecutor]] = {"executor": "ipython-embedded"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, EmbeddedIPythonCodeExecutor)

    config = {"executor": "commandline"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, CommandlineCodeExecutor)

    config = {"executor": EmbeddedIPythonCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, EmbeddedIPythonCodeExecutor)

    config = {"executor": CommandlineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, CommandlineCodeExecutor)

    config = {"executor": "unknown"}
    with pytest.raises(ValueError, match="Unknown code executor unknown"):
        executor = CodeExecutorFactory.create(config)

    config = {}
    with pytest.raises(ValueError, match="Unknown code executor None"):
        executor = CodeExecutorFactory.create(config)
