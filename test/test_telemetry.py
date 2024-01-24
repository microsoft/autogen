import pytest
import autogen
import autogen.telemetry
import uuid
import sys
import os
import json
from unittest.mock import Mock

WRAPPER_ID = 140610167717744
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
    "wrapper_id": WRAPPER_ID,
    "request": SAMPLE_CHAT_REQUEST,
    "response": SAMPLE_CHAT_RESPONSE,
    "is_cached": 0,
    "client_config": {"model": "gpt-4", "api_type": "azure"},
    "cost": 0.347,
    "start_time": autogen.telemetry.get_current_ts(),
}

SAMPLE_AGENT_INIT_ARGS = {
    "name": "teacher",
    "system_message": "some system message",
    "is_termination_msg": None,
    "max_consecutive_auto_reply": 2,
    "human_input_mode": "NEVER",
    "function_map": None,
    "code_execution_config": False,
    "llm_config": {
        "config_list": [
            {"model": "gpt-4", "base_url": "some base url", "api_type": "azure", "api_version": "2023-12-01-preview"}
        ]
    },
    "default_auto_reply": "",
    "description": None,
}

SAMPLE_LOG_NEW_AGENT_ARGS = {
    "wrapper_id": WRAPPER_ID,
    "agent": SAMPLE_AGENT_INIT_ARGS,
}

# skip id, session_id
COMPLETION_QUERY = """
    SELECT invocation_id, client_id, wrapper_id, request, response, is_cached,
        client_config, cost, start_time, end_time FROM chat_completions
"""

AGENT_QUERY = """
    SELECT wrapper_id, agent FROM agents
"""

###############################################################


def test_log_completion():
    autogen.telemetry.start_logging(dbname=":memory:")
    autogen.telemetry.log_chat_completion(**SAMPLE_LOG_CHAT_COMPLETION_ARGS)

    con = autogen.telemetry.get_connection()
    cur = con.cursor()

    for row in cur.execute(COMPLETION_QUERY):
        for (idx, val), arg in zip(enumerate(row), SAMPLE_LOG_CHAT_COMPLETION_ARGS.values()):
            # request, response, client_config
            if idx == 3 or idx == 4 or idx == 6:
                val = json.loads(val)
            assert val == arg
    autogen.telemetry.stop_logging()


def test_log_completion_with_none_response():
    SAMPLE_LOG_CHAT_COMPLETION_ARGS["response"] = None

    autogen.telemetry.start_logging(dbname=":memory:")
    autogen.telemetry.log_chat_completion(**SAMPLE_LOG_CHAT_COMPLETION_ARGS)

    con = autogen.telemetry.get_connection()
    cur = con.cursor()

    for row in cur.execute(COMPLETION_QUERY):
        for (idx, val), arg in zip(enumerate(row), SAMPLE_LOG_CHAT_COMPLETION_ARGS.values()):
            if idx == 4:  # response
                assert val == ""
                continue
            elif idx == 3 or idx == 6:  # request, client_config
                val = json.loads(val)
            assert val == arg
    autogen.telemetry.stop_logging()


def test_log_new_agent():
    autogen.telemetry.start_logging(dbname=":memory:")

    mock_agent = Mock()
    mock_agent.client = Mock()
    mock_agent.client.wrapper_id = WRAPPER_ID
    autogen.telemetry.log_new_agent(mock_agent, SAMPLE_AGENT_INIT_ARGS)

    con = autogen.telemetry.get_connection()
    cur = con.cursor()

    for row in cur.execute(AGENT_QUERY):
        for (idx, val), arg in zip(enumerate(row), SAMPLE_LOG_NEW_AGENT_ARGS.values()):
            if idx == 1:  # agent
                val = json.loads(val)
            assert val == arg

    autogen.telemetry.stop_logging()
