import pytest
from autogen.coding.commandline_code_executor import CommandlineCodeExecutor
from autogen.coding.factory import CodeExecutorFactory
from autogen.coding.ipython_code_executor import IPythonCodeExecutor


def test_create():
    config = {"executor": "ipython"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, IPythonCodeExecutor)

    config = {"executor": "commandline"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, CommandlineCodeExecutor)

    config = {"executor": IPythonCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, IPythonCodeExecutor)

    config = {"executor": CommandlineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, CommandlineCodeExecutor)

    config = {"executor": "unknown"}
    with pytest.raises(ValueError, match="Unknown code executor unknown"):
        executor = CodeExecutorFactory.create(config)

    config = {}
    with pytest.raises(ValueError, match="Unknown code executor None"):
        executor = CodeExecutorFactory.create(config)
