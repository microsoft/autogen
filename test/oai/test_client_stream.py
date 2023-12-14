import pytest
from autogen import OpenAIWrapper, config_list_from_json, config_list_openai_aoai
from test_utils import OAI_CONFIG_LIST, KEY_LOC

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_aoai_chat_completion_stream():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_completion_stream():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "1+1="}], stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_functions_stream():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"model": ["gpt-3.5-turbo"]},
    )
    functions = [
        {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                },
                "required": ["location"],
            },
        },
    ]
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[{"role": "user", "content": "What's the weather like today in San Francisco?"}],
        functions=functions,
        stream=True,
    )
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_completion_stream():
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=", model="gpt-3.5-turbo-instruct", stream=True)
    print(response)
    print(client.extract_text_or_completion_object(response))


if __name__ == "__main__":
    test_aoai_chat_completion_stream()
    test_chat_completion_stream()
    test_chat_functions_stream()
    test_completion_stream()
