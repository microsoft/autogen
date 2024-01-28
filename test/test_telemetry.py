import autogen
import autogen.telemetry
import uuid
import json
import pytest
import sqlite3
from conftest import skip_openai
from unittest.mock import Mock

try:
    import openai
except ImportError:
    skip = True
    AzureOpenAI = object
else:
    skip = False or skip_openai
    from openai import AzureOpenAI


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

SAMPLE_LOG_CHAT_COMPLETION_ARGS = {
    "invocation_id": str(uuid.uuid4()),
    "client_id": 140609438577184,
    "wrapper_id": 140610167717744,
    "request": SAMPLE_CHAT_REQUEST,
    "response": SAMPLE_CHAT_RESPONSE,
    "is_cached": 0,
    "cost": 0.347,
    "start_time": autogen.telemetry.get_current_ts(),
}


# skip id, session_id
COMPLETION_QUERY = """
    SELECT invocation_id, client_id, wrapper_id, request, response, is_cached,
        cost, start_time, end_time FROM chat_completions
"""

###############################################################


def test_log_completion():
    autogen.telemetry.start_logging(dbname=":memory:")
    autogen.telemetry.log_chat_completion(**SAMPLE_LOG_CHAT_COMPLETION_ARGS)

    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    for row in cur.execute(COMPLETION_QUERY):
        for key, arg in zip(row.keys(), SAMPLE_LOG_CHAT_COMPLETION_ARGS.values()):
            val = row[key]
            if key == "request" or key == "response":
                val = json.loads(val)
            assert val == arg
    autogen.telemetry.stop_logging()


def test_log_completion_with_none_response():
    SAMPLE_LOG_CHAT_COMPLETION_ARGS["response"] = None

    autogen.telemetry.start_logging(dbname=":memory:")
    autogen.telemetry.log_chat_completion(**SAMPLE_LOG_CHAT_COMPLETION_ARGS)

    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    for row in cur.execute(COMPLETION_QUERY):
        for key, arg in zip(row.keys(), SAMPLE_LOG_CHAT_COMPLETION_ARGS.values()):
            val = row[key]
            if key == "response":
                assert val == ""
                continue
            elif key == "request":
                val = json.loads(val)
            assert val == arg
    autogen.telemetry.stop_logging()


def test_log_new_agent():
    from autogen import AssistantAgent

    autogen.telemetry.start_logging(dbname=":memory:")
    agent_name = "some_assistant"
    config_list = [{"model": "gpt-4", "api_key": "some_key"}]

    agent = AssistantAgent(agent_name, llm_config={"config_list": config_list})
    init_args = {
        "foo": "bar",
        "baz": {
            "other_key": "other_val"
        },
        "a": None
    }

    autogen.telemetry.log_new_agent(agent, init_args)
    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT session_id, name, class, init_args FROM agents
    """

    for row in cur.execute(query):
        assert row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"], "session id is not valid uuid"
        assert row["name"] == agent_name
        assert row["class"] == "AssistantAgent"
        assert row["init_args"] == json.dumps(init_args)
    autogen.telemetry.stop_logging()


def test_log_oai_wrapper():
    from autogen import OpenAIWrapper

    autogen.telemetry.start_logging(dbname=":memory:")

    llm_config = {
        "config_list": [{"model": "gpt-4", "api_key": "some_key"}]
    }
    init_args = {
        'llm_config': llm_config,
        'base_config': {}
    }
    wrapper = OpenAIWrapper(**llm_config)

    autogen.telemetry.log_new_wrapper(wrapper, init_args)
    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT session_id, init_args FROM oai_wrappers
    """

    for row in cur.execute(query):
        assert row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"], "session id is not valid uuid"
        saved_init_args = json.loads(row["init_args"])
        assert 'config_list' in saved_init_args
        assert 'api_key' not in saved_init_args["config_list"][0]
        assert 'base_config' in saved_init_args
    autogen.telemetry.stop_logging()


@pytest.mark.skipif(skip, reason="openai not installed")
def test_log_oai_client():
    autogen.telemetry.start_logging(dbname="foo.db")

    openai_config = {
        'api_key': 'some_key',
        'api_version': '2023-12-01-preview',
        'azure_deployment': 'gpt-4',
        'azure_endpoint': 'https://foobar.openai.azure.com/'
    }
    client = AzureOpenAI(**openai_config)

    autogen.telemetry.log_new_client(client, Mock(), openai_config)

    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT session_id, init_args, class FROM oai_clients
    """

    for row in cur.execute(query):
        assert row["session_id"] and str(uuid.UUID(row["session_id"], version=4)) == row["session_id"], "session id is not valid uuid"
        assert row["class"] == "AzureOpenAI"
        saved_init_args = json.loads(row["init_args"])
        assert 'api_version' in saved_init_args
        assert 'api_key' not in saved_init_args
    autogen.telemetry.stop_logging()
