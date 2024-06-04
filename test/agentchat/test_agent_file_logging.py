import json
import os
import sys
import tempfile
import uuid
from typing import Any, Callable

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from conftest import skip_openai  # noqa: E402
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

import autogen
import autogen.runtime_logging
from autogen.logger.file_logger import FileLogger

is_windows = sys.platform.startswith("win")


def dummy_function(param1: str, param2: int) -> Any:
    return param1 * param2


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
@pytest.fixture
def logger() -> FileLogger:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    with tempfile.TemporaryDirectory(dir=current_dir) as temp_dir:
        log_file = os.path.join(temp_dir, "test_log.log")
        config = {"filename": log_file}
        logger = FileLogger(config)
        yield logger

    logger.stop()


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_start(logger: FileLogger):
    session_id = logger.start()
    assert isinstance(session_id, str)
    assert len(session_id) == 36


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_chat_completion(logger: FileLogger):
    invocation_id = uuid.uuid4()
    client_id = 123456789
    wrapper_id = 987654321
    request = {"messages": [{"content": "Test message", "role": "user"}]}
    response = "Test response"
    is_cached = 0
    cost = 0.5
    start_time = "2024-05-06 15:20:21.263231"
    agent = autogen.AssistantAgent(name="TestAgent", code_execution_config=False)

    logger.log_chat_completion(
        invocation_id=invocation_id,
        client_id=client_id,
        wrapper_id=wrapper_id,
        request=request,
        response=response,
        is_cached=is_cached,
        cost=cost,
        start_time=start_time,
        source=agent,
    )

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        log_data = json.loads(lines[0])
        assert log_data["invocation_id"] == str(invocation_id)
        assert log_data["client_id"] == client_id
        assert log_data["wrapper_id"] == wrapper_id
        assert log_data["response"] == response
        assert log_data["is_cached"] == is_cached
        assert log_data["cost"] == cost
        assert log_data["start_time"] == start_time
        assert log_data["source_name"] == "TestAgent"
        assert isinstance(log_data["thread_id"], int)


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_function_use(logger: FileLogger):
    source = autogen.AssistantAgent(name="TestAgent", code_execution_config=False)
    func: Callable[[str, int], Any] = dummy_function
    args = {"foo": "bar"}
    returns = True

    logger.log_function_use(source=source, function=func, args=args, returns=returns)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        log_data = json.loads(lines[0])
        assert log_data["source_name"] == "TestAgent"
        assert log_data["input_args"] == json.dumps(args)
        assert log_data["returns"] == json.dumps(returns)
        assert isinstance(log_data["thread_id"], int)


class TestWrapper:
    def __init__(self, init_args):
        self.init_args = init_args


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_new_agent(logger: FileLogger):
    agent = autogen.UserProxyAgent(name="user_proxy", code_execution_config=False)
    logger.log_new_agent(agent)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[0])  # the first line is the session id
        assert log_data["agent_name"] == "user_proxy"


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_event(logger: FileLogger):
    source = autogen.AssistantAgent(name="TestAgent", code_execution_config=False)
    name = "TestEvent"
    kwargs = {"key": "value"}
    logger.log_event(source, name, **kwargs)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[0])
        assert log_data["source_name"] == "TestAgent"
        assert log_data["event_name"] == name
        assert log_data["json_state"] == json.dumps(kwargs)
        assert isinstance(log_data["thread_id"], int)


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_new_wrapper(logger: FileLogger):
    wrapper = TestWrapper(init_args={"foo": "bar"})
    logger.log_new_wrapper(wrapper, wrapper.init_args)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[0])
        assert log_data["wrapper_id"] == id(wrapper)
        assert log_data["json_state"] == json.dumps(wrapper.init_args)
        assert isinstance(log_data["thread_id"], int)


@pytest.mark.skipif(is_windows, reason="Skipping file logging tests on Windows")
def test_log_new_client(logger: FileLogger):
    client = autogen.UserProxyAgent(name="user_proxy", code_execution_config=False)
    wrapper = TestWrapper(init_args={"foo": "bar"})
    init_args = {"foo": "bar"}
    logger.log_new_client(client, wrapper, init_args)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[0])
        assert log_data["client_id"] == id(client)
        assert log_data["wrapper_id"] == id(wrapper)
        assert log_data["json_state"] == json.dumps(init_args)
        assert isinstance(log_data["thread_id"], int)
