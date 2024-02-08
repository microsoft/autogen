import pytest
from unittest import mock

from autogen.agentchat.contrib.rag.utils import lazy_import, lazy_imported


@pytest.fixture
def mock_logger():
    with mock.patch("autogen.agentchat.contrib.rag.utils.logger") as mock_logger:
        yield mock_logger


def test_lazy_import_success(mock_logger):
    module_name = "os"
    module = lazy_import(module_name)
    assert module is not None
    assert module_name in lazy_imported
    mock_logger.error.assert_not_called()


def test_lazy_import_failure(mock_logger):
    module_name = "nonexistent_module"
    module = lazy_import(module_name)
    assert module is None
    assert module_name not in lazy_imported
    mock_logger.error.assert_called_once_with(f"Failed to import {module_name}.")


def test_lazy_import_attr_success(mock_logger):
    module_name = "autogen.agentchat"
    attr_name = "Agent"
    attr = lazy_import(module_name, attr_name)
    assert attr is not None
    assert module_name in lazy_imported
    mock_logger.error.assert_not_called()


def test_lazy_import_attr_failure(mock_logger):
    module_name = "os"
    attr_name = "nonexistent_attr"
    attr = lazy_import(module_name, attr_name)
    assert attr is None
    assert module_name in lazy_imported
    mock_logger.error.assert_called_once_with(f"Failed to import {attr_name} from {module_name}")


if __name__ == "__main__":
    pytest.main()
