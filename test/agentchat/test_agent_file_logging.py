import json
import os
import sys
import uuid

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from conftest import skip_openai  # noqa: E402
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

import autogen
import autogen.runtime_logging
from autogen.logger.file_logger import FileLogger


@pytest.fixture
def logger():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(project_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "test.log")
    config = {"filename": log_file}
    logger = FileLogger(config)
    yield logger
    with open(logger.log_file, "w") as f:
        f.truncate(0)


def test_start(logger):
    session_id = logger.start()
    assert isinstance(session_id, str)
    assert len(session_id) == 36


def test_log_chat_completion(logger):
    invocation_id = uuid.uuid4()
    client_id = 123456789
    wrapper_id = 987654321
    request = {"messages": [{"content": "Test message", "role": "user"}]}
    response = "Test response"
    is_cached = 0
    cost = 0.5
    start_time = "2024-05-06 15:20:21.263231"

    logger.log_chat_completion(invocation_id, client_id, wrapper_id, request, response, is_cached, cost, start_time)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        log_data = json.loads(lines[1])
        assert log_data["invocation_id"] == str(invocation_id)
        assert log_data["client_id"] == client_id
        assert log_data["wrapper_id"] == wrapper_id
        assert log_data["response"] == response
        assert log_data["is_cached"] == is_cached
        assert log_data["cost"] == cost
        assert log_data["start_time"] == start_time


class TestAgent:
    def __init__(self, name, init_args):
        self.name = name
        self.init_args = init_args


class TestWrapper:
    def __init__(self, init_args):
        self.init_args = init_args


def test_log_new_agent(logger):
    agent = TestAgent(name="TestAgent", init_args={"foo": "bar"})
    logger.log_new_agent(agent, agent.init_args)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[1])  # the first line is the session id
        assert log_data["agent_name"] == "TestAgent"
        assert log_data["args"] == agent.init_args


def test_log_event(logger):
    source = "TestSource"
    name = "TestEvent"
    kwargs = {"key": "value"}
    logger.log_event(source, name, **kwargs)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[2])  # the first two lines are session id and chat completion
        assert log_data["source_name"] == source
        assert log_data["event_name"] == name
        assert log_data["json_state"] == json.dumps(kwargs)


def test_log_new_wrapper(logger):
    wrapper = TestWrapper(init_args={"foo": "bar"})
    logger.log_new_wrapper(wrapper, wrapper.init_args)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[3])  # the first three lines are session id, chat completion, and event
        assert log_data["wrapper_id"] == id(wrapper)
        assert log_data["json_state"] == json.dumps(wrapper.init_args)


def test_log_new_client(logger):
    client = TestAgent(name="TestClient", init_args={"foo": "bar"})
    wrapper = TestWrapper(init_args={"foo": "bar"})
    init_args = {"foo": "bar"}
    logger.log_new_client(client, wrapper, init_args)

    with open(logger.log_file, "r") as f:
        lines = f.readlines()
        log_data = json.loads(lines[4])  # the first four lines are session id, chat completion, event, and wrapper
        assert log_data["client_id"] == id(client)
        assert log_data["wrapper_id"] == id(wrapper)
        assert log_data["json_state"] == json.dumps(init_args)
