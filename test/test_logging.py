import json
import sqlite3
import uuid
from typing import Any, Callable
from unittest.mock import Mock, patch

import pytest
from openai import AzureOpenAI

import autogen.runtime_logging
from autogen.logger.logger_utils import get_current_ts, to_dict

SAMPLE_CHAT_REQUEST = json.loads(
    """
{
    "messages": [
        {
            "content": "You are roleplaying a high school student strugling with linear algebra. Regardless how well the teacher explains things to you, you just don't quite get it. Keep your questions short.",
            "role": "system"
        },
        {
            "content": "Can you explain the difference between eigenvalues and singular values again?",
            "role": "assistant"
        },
        {
            "content": "Certainly!\\n\\nEigenvalues are associated with square matrices. They are the scalars, \\u03bb, that satisfy the equation\\n\\nA*x = \\u03bb*x\\n\\nwhere A is a square matrix, x is a nonzero vector (the eigenvector), and \\u03bb is the eigenvalue. The eigenvalue equation shows how the vector x is stretched or shrunk by the matrix A.\\n\\nSingular values, on the other hand, are associated with any m x n matrix, whether square or rectangular. They come from the matrix's singular value decomposition (SVD) and are the square roots of the non-negative eigenvalues of the matrix A*A^T or A^T*A (where A^T is the transpose of A). Singular values, denoted often by \\u03c3, represent the magnitude of the principal axes of the data's distribution and are always non-negative.\\n\\nTo sum up, eigenvalues relate to how a matrix scales vectors (specific to square matrices), while singular values give a measure of how a matrix stretches space (applicable to all matrices).",
            "role": "user"
        }
    ],
    "model": "gpt-4"
}
"""
)

SAMPLE_CHAT_RESPONSE = json.loads(
    """
{
    "id": "chatcmpl-8k57oSg1fz2JwpMcEOWMqUvwjf0cb",
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "logprobs": null,
            "message": {
                "content": "Oh, wait, I don't think I completely understand the concept of matrix multiplication. Could you break down how you multiply two matrices together?",
                "role": "assistant",
                "function_call": null,
                "tool_calls": null
            }
        }
    ],
    "created": 1705993480,
    "model": "gpt-4",
    "object": "chat.completion",
    "system_fingerprint": "fp_6d044fb900",
    "usage": {
        "completion_tokens": 28,
        "prompt_tokens": 274,
        "total_tokens": 302
    }
}
"""
)


def dummy_function(param1: str, param2: int) -> Any:
    return param1 * param2


###############################################################


@pytest.fixture(scope="function")
def db_connection():
    autogen.runtime_logging.start(config={"dbname": ":memory:"})
    con = autogen.runtime_logging.get_connection()
    con.row_factory = sqlite3.Row
    yield con

    autogen.runtime_logging.stop()


def get_sample_chat_completion(response):
    return {
        "invocation_id": str(uuid.uuid4()),
        "client_id": 140609438577184,
        "wrapper_id": 140610167717744,
        "request": SAMPLE_CHAT_REQUEST,
        "response": response,
        "is_cached": 0,
        "cost": 0.347,
        "start_time": get_current_ts(),
        "agent": autogen.AssistantAgent(name="TestAgent", code_execution_config=False),
    }


@pytest.mark.parametrize(
    "response, expected_logged_response",
    [
        (SAMPLE_CHAT_RESPONSE, SAMPLE_CHAT_RESPONSE),
        (None, {"response": None}),
        ("error in response", {"response": "error in response"}),
    ],
)
def test_log_completion(response, expected_logged_response, db_connection):
    cur = db_connection.cursor()

    sample_completion = get_sample_chat_completion(response)
    autogen.runtime_logging.log_chat_completion(**sample_completion)

    query = """
        SELECT invocation_id, client_id, wrapper_id, request, response, is_cached,
            cost, start_time, source_name FROM chat_completions
    """

    for row in cur.execute(query):
        assert row["invocation_id"] == sample_completion["invocation_id"]
        assert row["client_id"] == sample_completion["client_id"]
        assert row["wrapper_id"] == sample_completion["wrapper_id"]
        assert json.loads(row["request"]) == sample_completion["request"]
        assert json.loads(row["response"]) == expected_logged_response
        assert row["is_cached"] == sample_completion["is_cached"]
        assert row["cost"] == sample_completion["cost"]
        assert row["start_time"] == sample_completion["start_time"]
        assert row["source_name"] == "TestAgent"


def test_log_function_use(db_connection):
    cur = db_connection.cursor()

    source = autogen.AssistantAgent(name="TestAgent", code_execution_config=False)
    func: Callable[[str, int], Any] = dummy_function
    args = {"foo": "bar"}
    returns = True

    autogen.runtime_logging.log_function_use(agent=source, function=func, args=args, returns=returns)

    query = """
        SELECT source_id, source_name, function_name, args, returns, timestamp
        FROM function_calls
    """

    for row in cur.execute(query):
        assert row["source_name"] == "TestAgent"
        assert row["args"] == json.dumps(args)
        assert row["returns"] == json.dumps(returns)


def test_log_new_agent(db_connection):
    from autogen import AssistantAgent

    cur = db_connection.cursor()
    agent_name = "some_assistant"
    config_list = [{"model": "gpt-4", "api_key": "some_key"}]

    agent = AssistantAgent(agent_name, llm_config={"config_list": config_list})
    init_args = {"foo": "bar", "baz": {"other_key": "other_val"}, "a": None}

    autogen.runtime_logging.log_new_agent(agent, init_args)

    query = """
        SELECT session_id, name, class, init_args FROM agents
    """

    for row in cur.execute(query):
        assert (
            row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"]
        ), "session id is not valid uuid"
        assert row["name"] == agent_name
        assert row["class"] == "AssistantAgent"
        assert row["init_args"] == json.dumps(init_args)


def test_log_oai_wrapper(db_connection):
    from autogen import OpenAIWrapper

    cur = db_connection.cursor()

    llm_config = {"config_list": [{"model": "gpt-4", "api_key": "some_key", "base_url": "some url"}]}
    init_args = {"llm_config": llm_config, "base_config": {}}
    wrapper = OpenAIWrapper(**llm_config)

    autogen.runtime_logging.log_new_wrapper(wrapper, init_args)

    query = """
        SELECT session_id, init_args FROM oai_wrappers
    """

    for row in cur.execute(query):
        assert (
            row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"]
        ), "session id is not valid uuid"
        saved_init_args = json.loads(row["init_args"])
        assert "config_list" in saved_init_args
        assert "api_key" not in saved_init_args["config_list"][0]
        assert "base_url" not in saved_init_args["config_list"][0]
        assert "base_config" in saved_init_args


def test_log_oai_client(db_connection):
    cur = db_connection.cursor()

    openai_config = {
        "api_key": "some_key",
        "api_version": "2024-02-01",
        "azure_deployment": "gpt-4",
        "azure_endpoint": "https://foobar.openai.azure.com/",
    }
    client = AzureOpenAI(**openai_config)

    autogen.runtime_logging.log_new_client(client, Mock(), openai_config)

    query = """
        SELECT session_id, init_args, class FROM oai_clients
    """

    for row in cur.execute(query):
        assert (
            row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"]
        ), "session id is not valid uuid"
        assert row["class"] == "AzureOpenAI"
        saved_init_args = json.loads(row["init_args"])
        assert "api_version" in saved_init_args
        assert "api_key" not in saved_init_args


def test_to_dict():
    from autogen import Agent

    agent1 = autogen.ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )

    agent2 = autogen.ConversableAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
        function_map={"test_func": lambda x: x},
    )

    class Foo:
        def __init__(self):
            self.a = 1.234
            self.b = "some string"
            self.c = {"some_key": [7, 8, 9]}
            self.d = None
            self.test_function = lambda x, y: x + y
            self.extra_key = "remove this key"

    class Bar(object):
        def init(self):
            pass

        def build(self):
            self.foo_val = [Foo()]
            self.o = {"key_1": None, "key_2": [{"nested_key_1": ["nested_val_1", "nested_val_2"]}]}
            self.agents = [agent1, agent2]
            self.first_agent = agent1

    bar = Bar()
    bar.build()

    expected_foo_val_field = [
        {
            "a": 1.234,
            "b": "some string",
            "c": {"some_key": [7, 8, 9]},
            "d": None,
            "test_function": "self.test_function = lambda x, y: x + y",
        }
    ]

    expected_o_field = {"key_2": [{"nested_key_1": ["nested_val_1", "nested_val_2"]}]}

    result = to_dict(bar, exclude=("key_1", "extra_key"), no_recursive=(Agent))
    assert result["foo_val"] == expected_foo_val_field
    assert result["o"] == expected_o_field
    assert len(result["agents"]) == 2
    for agent in result["agents"]:
        assert "autogen.agentchat.conversable_agent.ConversableAgent" in agent
    assert "autogen.agentchat.conversable_agent.ConversableAgent" in result["first_agent"]


@patch("logging.Logger.error")
def test_logging_exception_will_not_crash_only_print_error(mock_logger_error, db_connection):
    sample_completion = get_sample_chat_completion(SAMPLE_CHAT_REQUEST)
    sample_completion["is_cached"] = {"foo": "bar"}

    autogen.runtime_logging.log_chat_completion(**sample_completion)

    args, _ = mock_logger_error.call_args
    error_message = args[0]
    assert error_message.startswith("[sqlite logger]Error running query with query")
