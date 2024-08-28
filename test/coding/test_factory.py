import pytest

from autogen.coding.factory import CodeExecutorFactory


def test_create_unknown() -> None:
    config = {"executor": "unknown"}
    with pytest.raises(ValueError, match="Unknown code executor unknown"):
        CodeExecutorFactory.create(config)

    config = {}
    with pytest.raises(ValueError, match="Unknown code executor None"):
        CodeExecutorFactory.create(config)
