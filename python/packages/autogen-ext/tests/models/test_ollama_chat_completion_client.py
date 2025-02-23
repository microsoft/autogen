from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core.models._types import UserMessage

import asyncio
import pytest

pytest_plugins = ('pytest_asyncio',)

@pytest.mark.asyncio
async def test_ollama_chat_completion_client_doesnt_error_with_host_kwarg():
    client = OllamaChatCompletionClient(
        model="llama3.1",
        host="http://testyhostname:11434",
        some_other_random_kwarg_that_should_be_automatically_removed_from_create_args="foobar"
    )

    ## Call to client.create will throw a ConnectionError, 
    # but that will only occur if the call to the AsyncChat's .chat() method does not receive unexpected kwargs
    # and does not throw a TypeError with unrecognized kwargs
    # (i.e. the extra unrecognized kwargs have been successfully removed)
    try:
        await client.create([UserMessage(content="hi", source="user")])
    except TypeError as e:
        assert "AsyncClient.chat() got an unexpected keyword argument" not in e.args[0]
    except ConnectionError as e:
        pass

