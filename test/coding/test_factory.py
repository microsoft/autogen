from typing import Dict, Union
import pytest
from autogen.coding.base import CodeExecutor
from autogen.coding.local_commandline_code_executor import LocalCommandlineCodeExecutor
from autogen.coding.factory import CodeExecutorFactory
from autogen.coding.embedded_ipython_code_executor import EmbeddedIPythonCodeExecutor


def test_create() -> None:
    config: Dict[str, Union[str, CodeExecutor]] = {"executor": "ipython-embedded"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, EmbeddedIPythonCodeExecutor)

    config = {"executor": "commandline-local"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, LocalCommandlineCodeExecutor)

    config = {"executor": EmbeddedIPythonCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert executor is config["executor"]

    config = {"executor": LocalCommandlineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert executor is config["executor"]

    config = {"executor": "unknown"}
    with pytest.raises(ValueError, match="Unknown code executor unknown"):
        executor = CodeExecutorFactory.create(config)

    config = {}
    with pytest.raises(ValueError, match="Unknown code executor None"):
        executor = CodeExecutorFactory.create(config)
