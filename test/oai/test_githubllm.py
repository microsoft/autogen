from unittest.mock import MagicMock, patch
import pytest

from autogen.oai.github import GithubClient, GithubWrapper

@pytest.fixture
def github_client():
    with patch.dict("os.environ", {"GITHUB_TOKEN": "fake_token", "AZURE_API_KEY": "fake_azure_key"}):
        return GithubClient(model="gpt-4o", system_prompt="Test prompt")


@pytest.fixture
def github_wrapper():
    with patch.dict("os.environ", {"GITHUB_TOKEN": "fake_token", "AZURE_API_KEY": "fake_azure_key"}):
        config = {"model": "gpt-4o", "system_prompt": "Test prompt", "use_azure_fallback": True}
        return GithubWrapper(config_list=[config])


def test_github_client_initialization(github_client):
    assert github_client.model == "gpt-4o"
    assert github_client.system_prompt == "Test prompt"
    assert github_client.use_azure_fallback == True


def test_github_client_unsupported_model():
    with pytest.raises(ValueError):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "fake_token", "AZURE_API_KEY": "fake_azure_key"}):
            GithubClient(model="unsupported-model")


@patch("requests.post")
def test_github_client_create(mock_post, github_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "test_id",
        "model": "gpt-4o",
        "created": 1234567890,
        "choices": [{"message": {"content": "Test response"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    mock_post.return_value = mock_response

    params = {"messages": [{"role": "user", "content": "Test message"}]}
    response = github_client.create(params)

    assert response.id == "test_id"
    assert response.model == "gpt-4o"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Test response"


def test_github_client_message_retrieval(github_client):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Response 1")),
        MagicMock(message=MagicMock(content="Response 2")),
    ]

    messages = github_client.message_retrieval(mock_response)
    assert messages == ["Response 1", "Response 2"]


def test_github_client_cost(github_client):
    mock_response = MagicMock()
    cost = github_client.cost(mock_response)
    assert cost == 0.0  # Assuming the placeholder implementation


def test_github_client_get_usage(github_client):
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30
    mock_response.model = "gpt-4o"

    usage = github_client.get_usage(mock_response)
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 20
    assert usage["total_tokens"] == 30
    assert usage["model"] == "gpt-4o"


@patch("autogen.oai.github.GithubClient.create")
def test_github_wrapper_create(mock_create, github_wrapper):
    mock_response = MagicMock()
    mock_create.return_value = mock_response

    params = {"messages": [{"role": "user", "content": "Test message"}]}
    response = github_wrapper.create(**params)

    assert response == mock_response
    assert hasattr(response, "config_id")
    mock_create.assert_called_once_with(params)

def test_github_wrapper_message_retrieval(github_wrapper):
    mock_response = MagicMock()
    mock_response.config_id = 0


    with patch.object(github_wrapper._clients[0], "message_retrieval") as mock_retrieval:
        mock_retrieval.return_value = ["Test message"]
        messages = github_wrapper.message_retrieval(mock_response)

    assert messages == ["Test message"]

def test_github_wrapper_cost(github_wrapper):
    mock_response = MagicMock()
    mock_response.config_id = 0

    with patch.object(github_wrapper._clients[0], "cost") as mock_cost:
        mock_cost.return_value = 0.05
        cost = github_wrapper.cost(mock_response)

    assert cost == 0.05


def test_github_wrapper_get_usage(github_wrapper):
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30
    mock_response.model = "gpt-4o"

    usage = github_wrapper.get_usage(mock_response)
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 20
    assert usage["total_tokens"] == 30
    assert usage["model"] == "gpt-4o"
