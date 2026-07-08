import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--windows", action="store_true", default=False, help="Run tests for Windows")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "windows: mark test as requiring Windows")
