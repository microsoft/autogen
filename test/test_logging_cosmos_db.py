import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from azure.cosmos import CosmosClient

import autogen.runtime_logging
from autogen.logger.cosmos_db_logger import CosmosDBLogger, CosmosDBLoggerConfig
from autogen.logger.logger_utils import get_current_ts, to_dict

# Sample data for testing
SAMPLE_CHAT_REQUEST = json.loads(
    """
{
    "messages": [
        {
            "content": "Can you explain the difference between eigenvalues and singular values again?",
            "role": "assistant"
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
            "message": {
                "content": "Eigenvalues are...",
                "role": "assistant"
            }
        }
    ],
    "model": "gpt-4"
}
"""
)


@pytest.fixture(scope="function")
def cosmos_db_config() -> CosmosDBLoggerConfig:
    return {
        "connection_string": "AccountEndpoint=https://example.documents.azure.com:443/;AccountKey=fakeKey;",
        "database_id": "TestDatabase",
        "container_id": "TestContainer",
    }


@pytest.fixture(scope="function")
def cosmos_logger(cosmos_db_config: CosmosDBLoggerConfig):
    with patch.object(CosmosClient, "from_connection_string", return_value=MagicMock()):
        logger = autogen.runtime_logging.CosmosDBLogger(cosmos_db_config)
        yield logger
        logger.stop()


def get_sample_chat_completion(response):
    return {
        "invocation_id": str(uuid.uuid4()),
        "client_id": 12345,
        "wrapper_id": 67890,
        "request": SAMPLE_CHAT_REQUEST,
        "response": response,
        "is_cached": 0,
        "cost": 0.347,
        "start_time": get_current_ts(),
    }


@patch("azure.cosmos.CosmosClient")
def test_log_chat_completion(mock_cosmos_client, cosmos_logger):
    sample_completion = get_sample_chat_completion(SAMPLE_CHAT_RESPONSE)
    cosmos_logger.log_chat_completion(**sample_completion)

    # Check if the document is correctly added to the queue
    assert not cosmos_logger.log_queue.empty()

    # Simulate processing the log entry
    document = cosmos_logger.log_queue.get()
    expected_keys = [
        "type",
        "invocation_id",
        "client_id",
        "wrapper_id",
        "session_id",
        "request",
        "response",
        "is_cached",
        "cost",
        "start_time",
        "end_time",
    ]
    assert all(key in document for key in expected_keys)

    # Check if the mock was called correctly
    mock_cosmos_client.from_connection_string.assert_called_once_with(cosmos_db_config["connection_string"])


@pytest.mark.parametrize(
    "response, expected_logged_response",
    [
        (SAMPLE_CHAT_RESPONSE, SAMPLE_CHAT_RESPONSE),
        (None, {"response": None}),
        ("error in response", {"response": "error in response"}),
    ],
)
def test_log_completion_variants(response, expected_logged_response, cosmos_logger):
    sample_completion = get_sample_chat_completion(response)
    cosmos_logger.log_chat_completion(**sample_completion)

    document = cosmos_logger.log_queue.get()
    if isinstance(expected_logged_response, dict):
        assert json.loads(document["response"]) == expected_logged_response
    else:
        assert document["response"] == to_dict(response)


def test_stop_logging(cosmos_logger):
    cosmos_logger.stop()
    # After stopping, the worker thread should no longer be active
    assert not cosmos_logger.logger_thread.is_alive()
