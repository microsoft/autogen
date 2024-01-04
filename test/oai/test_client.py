import pytest
from autogen import OpenAIWrapper, config_list_from_json, config_list_openai_aoai
from conftest import skip_openai

TOOL_ENABLED = False
try:
    from openai import OpenAI
    import openai

    if openai.__version__ >= "1.1.0":
        TOOL_ENABLED = True
    from openai.types.chat.chat_completion import ChatCompletionMessage
except ImportError:
    skip = True
else:
    skip = False or skip_openai

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_aoai_chat_completion():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    # for config in config_list:
    #     print(config)
    #     client = OpenAIWrapper(**config)
    #     response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip or not TOOL_ENABLED, reason="openai>=1.1.0 not installed")
def test_oai_tool_calling_extraction():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "model": ["gpt-3.5-turbo", "gpt-35-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(
        messages=[
            {
                "role": "user",
                "content": "What is the weather in San Francisco?",
            },
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "getCurrentWeather",
                    "description": "Get the weather in location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "The city and state e.g. San Francisco, CA"},
                            "unit": {"type": "string", "enum": ["c", "f"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ],
    )
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_completion():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "1+1="}])
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_completion():
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=", model="gpt-3.5-turbo-instruct")
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
@pytest.mark.parametrize(
    "cache_seed, model",
    [
        (None, "gpt-3.5-turbo-instruct"),
        (42, "gpt-3.5-turbo-instruct"),
    ],
)
def test_cost(cache_seed, model):
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list, cache_seed=cache_seed)
    response = client.create(prompt="1+3=", model=model)
    print(response.cost)


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_usage_summary():
    config_list = config_list_openai_aoai(KEY_LOC)
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+3=", model="gpt-3.5-turbo-instruct", cache_seed=None)

    # usage should be recorded
    assert client.actual_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"

    # check print
    client.print_usage_summary()

    # check update
    client._update_usage_summary(response, use_cache=True)
    assert (
        client.total_usage_summary["total_cost"] == response.cost * 2
    ), "total_cost should be equal to response.cost * 2"

    # check clear
    client.clear_usage_summary()
    assert client.actual_usage_summary is None, "actual_usage_summary should be None"
    assert client.total_usage_summary is None, "total_usage_summary should be None"

    # actual usage and all usage should be different
    response = client.create(prompt="1+3=", model="gpt-3.5-turbo-instruct", cache_seed=42)
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    assert client.actual_usage_summary is None, "No actual cost should be recorded"


if __name__ == "__main__":
    test_aoai_chat_completion()
    test_oai_tool_calling_extraction()
    test_chat_completion()
    test_completion()
    # test_cost()
    test_usage_summary()
