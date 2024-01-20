import pytest

skip_openai = False
skip_redis = False


# Registers command-line option '--skip-openai' and '--skip-redis' via pytest hook.
# When this flag is set, it indicates that tests requiring OpenAI should be skipped.
def pytest_addoption(parser):
    parser.addoption("--skip-openai", action="store_true", help="Skip all tests that require openai")
    parser.addoption("--skip-redis", action="store_true", help="Skip all tests that require redis")


# pytest hook implementation extracting the '--skip-openai' command line arg and exposing it globally
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    global skip_openai
    skip_openai = config.getoption("--skip-openai", False)
    global skip_redis
    skip_redis = config.getoption("--skip-redis", False)
