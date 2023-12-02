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


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
@pytest.mark.parametrize(
    "cache_seed, model",
    [
        (None, "gpt-3.5-turbo-instruct"),
        (42, "gpt-3.5-turbo-instruct"),
        (None, "text-ada-001"),
    ],
)
def test_cost(cache_seed, model):
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list, cache_seed=cache_seed)
    response = client.create(prompt="1+3=", model=model)
    print(response.cost)


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_create_with_different_models():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-3.5-turbo-instruct"]},
    )
    messages = [{"role": "user", "content": "2+2="}]

    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=", model="gpt-3.5-turbo-instruct")
    assert response.model in ["gpt-3.5-turbo-instruct", "gpt-35-turbo-instruct"], "Model not consistent."

    response = client.create(messages=messages, model="gpt-3.5-turbo")
    assert response.model in ["gpt-3.5-turbo", "gpt-35-turbo"], "Model not consistent."

    try:
        response = client.create(messages=messages, model="gpt-4")
    except ValueError as e:
        print(e)
    else:
        raise ValueError("Expected ValueError")


if __name__ == "__main__":
    test_aoai_chat_completion()
    test_chat_completion()
    test_completion()
    test_cost()
