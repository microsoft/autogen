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
    config = {
        "connection_string": "AccountEndpoint=https://example.documents.azure.com:443/;AccountKey=fakeKey;",
        "database_id": "TestDatabase",
        "container_id": "TestContainer",
    }
    autogen.runtime_logging.start(logger_type="cosmos", config=config)
    yield
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
    }

@patch("azure.cosmos.CosmosClient")
class TestCosmosDBLogging:
    @pytest.mark.parametrize(
        "response, expected_logged_response",
        [
            (SAMPLE_CHAT_RESPONSE, SAMPLE_CHAT_RESPONSE),
            (None, {"response": None}),
            ("error in response", {"response": "error in response"}),
        ],
    )
    def test_log_completion_cosmos(self, MockCosmosClient, cosmos_db_setup, response, expected_logged_response):
        mock_client = Mock()
        mock_database = Mock()
        mock_container = Mock()

        MockCosmosClient.from_connection_string.return_value = mock_client
        mock_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container

        sample_completion = get_sample_chat_completion(response)

        autogen.runtime_logging.log_chat_completion(**sample_completion)

        expected_document = {
            "type": "chat_completion",
            "invocation_id": sample_completion["invocation_id"],
            "client_id": sample_completion["client_id"],
            "wrapper_id": sample_completion["wrapper_id"],
            "session_id": mock_container.session_id,
            "request": sample_completion["request"],
            "response": expected_logged_response,
            "is_cached": sample_completion["is_cached"],
            "cost": sample_completion["cost"],
            "start_time": sample_completion["start_time"],
            "end_time": get_current_ts(),
        }

        mock_container.upsert_item.assert_called_once_with(expected_document)

    def test_log_new_entity(self, MockCosmosClient, cosmos_db_setup):
        mock_client = Mock()
        mock_database = Mock()
        mock_container = Mock()

        MockCosmosClient.from_connection_string.return_value = mock_client
        mock_client.get_database_client.return_value = mock_database
        mock_database.get_container_client.return_value = mock_container

        agent = ConversableAgent("Assistant", llm_config={"config_list": [{"model": "gpt-3"}]})
        init_args = {"name": "Assistant", "config": agent.llm_config}

        autogen.runtime_logging.log_new_agent(agent, init_args)
        autogen.runtime_logging.log_new_wrapper(OpenAIWrapper(), init_args)  # Simplified for example

        expected_document_agent = {
            "type": "new_agent",
            "session_id": mock_container.session_id,
            "agent_id": id(agent),
            "agent_name": agent.name,
            "init_args": to_dict(init_args),
            "timestamp": get_current_ts(),
        }
        expected_document_wrapper = {
            "type": "new_wrapper",
            "session_id": mock_container.session_id,
            "wrapper_id": id(OpenAIWrapper()),  # Not exactly the same instance but for example's sake
            "init_args": to_dict(init_args),
            "timestamp": get_current_ts(),
        }

        mock_container.upsert_item.assert_any_call(expected_document_agent)
        mock_container.upsert_item.assert_any_call(expected_document_wrapper)
