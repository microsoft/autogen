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
def test_aoai_chat_completion():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    # for config in config_list:
    #     print(config)
    #     client = OpenAIWrapper(**config)
    #     response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_function_call(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_completion():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "1+1="}])
    print(response)
    print(client.extract_text_or_function_call(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_completion():
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=", model="gpt-3.5-turbo-instruct")
    print(response)
    print(client.extract_text_or_function_call(response))


if __name__ == "__main__":
    test_aoai_chat_completion()
    test_chat_completion()
    test_completion()
