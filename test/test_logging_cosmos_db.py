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
def test_log_completion_cosmos(MockCosmosClient, cosmos_db_setup):
    mock_client = Mock()
    mock_database = Mock()
    mock_container = Mock()

    MockCosmosClient.from_connection_string.return_value = mock_client
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container

    # Use parametrization to test various cases
    @pytest.mark.parametrize(
        "response, expected_logged_response",
        [
            (SAMPLE_CHAT_RESPONSE, SAMPLE_CHAT_RESPONSE),
            (None, {"response": None}),
            ("error in response", {"response": "error in response"}),
        ],
    )
    def inner_test_log(response, expected_logged_response):
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

    inner_test_log()


@patch("azure.cosmos.CosmosClient")
def test_log_new_agent_cosmos(MockCosmosClient, cosmos_db_setup):
    mock_client = Mock()
    mock_database = Mock()
    mock_container = Mock()

    MockCosmosClient.from_connection_string.return_value = mock_client
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container

    agent_name = "some_assistant"
    config_list = [{"model": "gpt-4", "api_key": "some_key"}]
    agent = AssistantAgent(agent_name, llm_config={"config_list": config_list})
    init_args = {"foo": "bar", "baz": {"other_key": "other_val"}, "a": None}

    autogen.runtime_logging.log_new_agent(agent, init_args)

    expected_document = {
        "type": "new_agent",
        "session_id": mock_container.session_id,  # This will need to match the actual session id used in the logger
        "agent_id": id(agent),
        "agent_name": agent.name,
        "init_args": to_dict(init_args),
        "timestamp": get_current_ts(),
    }

    mock_container.upsert_item.assert_called_once_with(expected_document)

@patch("azure.cosmos.CosmosClient")
def test_log_oai_wrapper_cosmos(MockCosmosClient, cosmos_db_setup):
    mock_client = Mock()
    mock_database = Mock()
    mock_container = Mock()

    MockCosmosClient.from_connection_string.return_value = mock_client
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container

    llm_config = {"config_list": [{"model": "gpt-4", "api_key": "some_key", "base_url": "some url"}]}
    init_args = {"llm_config": llm_config, "base_config": {}}
    wrapper = OpenAIWrapper(**llm_config)

    autogen.runtime_logging.log_new_wrapper(wrapper, init_args)

    expected_document = {
        "type": "new_wrapper",
        "session_id": mock_container.session_id,
        "wrapper_id": id(wrapper),
        "init_args": to_dict(init_args, exclude=("api_key", "base_url")),
        "timestamp": get_current_ts(),
    }

    mock_container.upsert_item.assert_called_once_with(expected_document)

@patch("azure.cosmos.CosmosClient")
def test_log_oai_client_cosmos(MockCosmosClient, cosmos_db_setup):
    mock_client = Mock()
    mock_database = Mock()
    mock_container = Mock()

    MockCosmosClient.from_connection_string.return_value = mock_client
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container

    openai_config = {
        "api_key": "some_key",
        "api_version": "2024-02-15-preview",
        "azure_deployment": "gpt-4",
        "azure_endpoint": "https://foobar.openai.azure.com/",
    }
    client = AzureOpenAI(**openai_config)

    autogen.runtime_logging.log_new_client(client, Mock(), openai_config)

    expected_document = {
        "type": "new_client",
        "session_id": mock_container.session_id,
        "client_id": id(client),
        "wrapper_id": id(Mock()),
        "client_class": type(client).__name__,
        "init_args": to_dict(openai_config, exclude=("api_key", "azure_endpoint")),
        "timestamp": get_current_ts(),
    }

    mock_container.upsert_item.assert_called_once_with(expected_document)


def test_to_dict():
    from autogen import Agent

    agent1 = ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )

    agent2 = ConversableAgent(
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


@patch("azure.cosmos.CosmosClient")
def test_logging_exception_will_not_crash_only_print_error(MockCosmosClient, cosmos_db_setup, caplog):
    mock_client = Mock()
    mock_database = Mock()
    mock_container = Mock()
    MockCosmosClient.from_connection_string.return_value = mock_client
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container

    sample_completion = {
        "invocation_id": str(uuid.uuid4()),
        "client_id": 140609438577184,
        "wrapper_id": 140610167717744,
        "request": SAMPLE_CHAT_REQUEST,
        "response": SAMPLE_CHAT_RESPONSE,
        "is_cached": {"foo": "bar"},  # This will cause a serialization error
        "cost": 0.347,
        "start_time": get_current_ts(),
    }

    autogen.runtime_logging.log_chat_completion(**sample_completion)

    assert "Error processing log entry" in caplog.text
