import json
import uuid
from unittest.mock import Mock, patch

import pytest
from openai import AzureOpenAI

import autogen.runtime_logging
from autogen import AssistantAgent, OpenAIWrapper, ConversableAgent
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
def cosmos_db_setup():
    with patch('azure.cosmos.CosmosClient') as MockCosmosClient, \
         patch('azure.cosmos.CosmosClient.from_connection_string') as mock_from_conn_str, \
         patch('azure.cosmos.auth._get_authorization_header') as mock_auth_header:
        mock_client = Mock()
        mock_database = Mock()
        mock_container = Mock()
        mock_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container
        mock_from_conn_str.return_value = mock_client
        mock_auth_header.return_value = "Mocked Auth Header"  # Mock deeper authorization functions if necessary

        config = {
            "connection_string": "AccountEndpoint=https://example.documents.azure.com:443/;AccountKey=dGVzdA==",
            "database_id": "TestDatabase",
            "container_id": "TestContainer",
        }
        
        from autogen.runtime_logging import start, stop
        start(logger_type="cosmos", config=config)
        yield mock_container
        stop()

@pytest.mark.usefixtures("cosmos_db_setup")
class TestCosmosDBLogging:
    def get_sample_chat_completion(self, response):
        return {
            "invocation_id": str(uuid.uuid4()),
            "client_id": 140609438577184,
            "wrapper_id": 140610167717744,
            "request": SAMPLE_CHAT_REQUEST,
            "response": response,
            "is_cached": 0,
            "cost": 0.347,
            "start_time": get_current_ts(),
        }

    def test_log_completion_cosmos(self, mock_container):
        sample_completion = self.get_sample_chat_completion(SAMPLE_CHAT_RESPONSE)
        autogen.runtime_logging.log_chat_completion(**sample_completion)

        expected_document = {
            "type": "chat_completion",
            "invocation_id": sample_completion["invocation_id"],
            "client_id": sample_completion["client_id"],
            "wrapper_id": sample_completion["wrapper_id"],
            "session_id": mock_container.session_id,
            "request": sample_completion["request"],
            "response": SAMPLE_CHAT_RESPONSE,
            "is_cached": sample_completion["is_cached"],
            "cost": sample_completion["cost"],
            "start_time": sample_completion["start_time"],
            "end_time": get_current_ts(),
        }

        mock_container.upsert_item.assert_called_once_with(expected_document)
