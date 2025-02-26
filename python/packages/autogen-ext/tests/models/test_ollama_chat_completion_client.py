from typing import Any, Mapping

import pytest
from autogen_core.models._types import UserMessage
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.ollama._ollama_client import OLLAMA_VALID_CREATE_KWARGS_KEYS
from httpx import Response
from ollama import AsyncClient


def _mock_request(*args: Any, **kwargs: Any) -> Response:
    return Response(status_code=200, content="{'response': 'Hello world!'}")


@pytest.mark.asyncio
async def test_ollama_chat_completion_client_doesnt_error_with_host_kwarg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AsyncClient, "_request", _mock_request)

    client = OllamaChatCompletionClient(model="llama3.1", host="http://testyhostname:11434")

    ## Call to client.create will throw a ConnectionError,
    # but that will only occur if the call to the AsyncChat's .chat() method does not receive unexpected kwargs
    # and does not throw a TypeError with unrecognized kwargs
    # (i.e. the extra unrecognized kwargs have been successfully removed)
    try:
        await client.create([UserMessage(content="hi", source="user")])
    except TypeError as e:
        assert "AsyncClient.chat() got an unexpected keyword argument" not in e.args[0]


def test_create_args_from_config_drops_unexpected_kwargs() -> None:
    test_config: Mapping[str, Any] = {
        "model": "llama3.1",
        "messages": [],
        "tools": [],
        "stream": False,
        "format": "json",
        "options": {},
        "keep_alive": 100,
        "extra_unexpected_kwarg": "value",
        "another_extra_unexpected_kwarg": "another_value",
    }

    client = OllamaChatCompletionClient(**test_config)

    final_create_args = client.get_create_args()

    for arg in final_create_args.keys():
        assert arg in OLLAMA_VALID_CREATE_KWARGS_KEYS
