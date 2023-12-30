import pytest

skip_openai = False


# Registers command-line option '--skip-openai' via pytest hook.
# When this flag is set, it indicates that tests requiring OpenAI should be skipped.
def pytest_addoption(parser):
    parser.addoption("--skip-openai", action="store_true", help="Skip all tests that require openai")


# pytest hook implementation extracting the '--skip-openai' command line arg and exposing it globally
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    global skip_openai
    skip_openai = config.getoption("--skip-openai", False)
