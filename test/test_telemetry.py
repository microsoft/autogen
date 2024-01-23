import pytest
import autogen
import autogen.telemetry
import uuid
import sys
import os
import json

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
    "client_config": {"model": "gpt-4", "api_type": "azure"},
    "cost": 0.347,
    "start_time": autogen.telemetry.get_current_ts(),
}

###############################################################


def test_telemetry():
    autogen.telemetry.start_logging(dbname=":memory:")

    # Add something to the log
    autogen.telemetry.log_chat_completion(**SAMPLE_LOG_CHAT_COMPLETION_ARGS)

    # Check what's in the db
    con = autogen.telemetry.get_connection()
    cur = con.cursor()
    for row in cur.execute(
        "SELECT id, invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, client_config, cost, start_time, end_time FROM chat_completions;"
    ):
        assert row[1] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["invocation_id"]
        assert row[2] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["client_id"]
        assert row[3] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["wrapper_id"]
        assert json.loads(row[5]) == SAMPLE_LOG_CHAT_COMPLETION_ARGS["request"]
        assert json.loads(row[6]) == SAMPLE_LOG_CHAT_COMPLETION_ARGS["response"]
        assert row[7] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["is_cached"]
        assert json.loads(row[8]) == SAMPLE_LOG_CHAT_COMPLETION_ARGS["client_config"]
        assert row[9] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["cost"]
        assert row[10] == SAMPLE_LOG_CHAT_COMPLETION_ARGS["start_time"]

    autogen.telemetry.stop_logging()


if __name__ == "__main__":
    test_telemetry()
