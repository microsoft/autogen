#!/usr/bin/env python3 -m pytest

import os
import shutil
import sys
import time

import pytest

from autogen import OpenAIWrapper, config_list_from_json
from autogen.cache.cache import Cache
from autogen.oai.client import LEGACY_CACHE_DIR, LEGACY_DEFAULT_CACHE_SEED

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

TOOL_ENABLED = False
try:
    import openai
    from openai import OpenAI

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
        filter_dict={"api_type": ["azure"], "tags": ["gpt-3.5-turbo"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_completion_object(response))

    # test dialect
    config = config_list[0]
    config["azure_deployment"] = config["model"]
    config["azure_endpoint"] = config.pop("base_url")
    client = OpenAIWrapper(**config)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip or not TOOL_ENABLED, reason="openai>=1.1.0 not installed")
def test_oai_tool_calling_extraction():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "tags": ["gpt-3.5-turbo"]},
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
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-35-turbo-instruct", "gpt-3.5-turbo-instruct"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+1=")
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
@pytest.mark.parametrize(
    "cache_seed",
    [
        None,
        42,
    ],
)
def test_cost(cache_seed):
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-35-turbo-instruct", "gpt-3.5-turbo-instruct"]},
    )
    client = OpenAIWrapper(config_list=config_list, cache_seed=cache_seed)
    response = client.create(prompt="1+3=")
    print(response.cost)


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_customized_cost():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"tags": ["gpt-3.5-turbo-instruct"]}
    )
    for config in config_list:
        config.update({"price": [1000, 1000]})
    client = OpenAIWrapper(config_list=config_list, cache_seed=None)
    response = client.create(prompt="1+3=")
    assert (
        response.cost >= 4
    ), f"Due to customized pricing, cost should be > 4. Message: {response.choices[0].message.content}"


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_usage_summary():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-35-turbo-instruct", "gpt-3.5-turbo-instruct"]},
    )
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(prompt="1+3=", cache_seed=None)

    # usage should be recorded
    assert client.actual_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"

    # check print
    client.print_usage_summary()

    # check clear
    client.clear_usage_summary()
    assert client.actual_usage_summary is None, "actual_usage_summary should be None"
    assert client.total_usage_summary is None, "total_usage_summary should be None"

    # actual usage and all usage should be different
    response = client.create(prompt="1+3=", cache_seed=42)
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    client.clear_usage_summary()
    response = client.create(prompt="1+3=", cache_seed=42)
    assert client.actual_usage_summary is None, "No actual cost should be recorded"

    # check update
    response = client.create(prompt="1+3=", cache_seed=42)
    assert (
        client.total_usage_summary["total_cost"] == response.cost * 2
    ), "total_cost should be equal to response.cost * 2"


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_legacy_cache():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-3.5-turbo"]},
    )

    # Prompt to use for testing.
    prompt = "Write a 100 word summary on the topic of the history of human civilization."

    # Clear cache.
    if os.path.exists(LEGACY_CACHE_DIR):
        shutil.rmtree(LEGACY_CACHE_DIR)

    # Test default cache seed.
    client = OpenAIWrapper(config_list=config_list)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test with cache seed set through constructor
    client = OpenAIWrapper(config_list=config_list, cache_seed=13)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(13)))

    # Test with cache seed set through create method
    client = OpenAIWrapper(config_list=config_list)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=17)
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=17)
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(17)))

    # Test using a different cache seed through create method.
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=21)
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(21)))


@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_cache():
    config_list = config_list_from_json(
        env_or_file=OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-3.5-turbo"]},
    )

    # Prompt to use for testing.
    prompt = "Write a 100 word summary on the topic of the history of artificial intelligence."

    # Clear cache.
    if os.path.exists(LEGACY_CACHE_DIR):
        shutil.rmtree(LEGACY_CACHE_DIR)
    cache_dir = ".cache_test"
    assert cache_dir != LEGACY_CACHE_DIR
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    # Test cache set through constructor.
    with Cache.disk(cache_seed=49, cache_path_root=cache_dir) as cache:
        client = OpenAIWrapper(config_list=config_list, cache=cache)
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_response == warm_cache_response
        assert duration_with_warm_cache < duration_with_cold_cache
        assert os.path.exists(os.path.join(cache_dir, str(49)))
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(49)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test cache set through method.
    client = OpenAIWrapper(config_list=config_list)
    with Cache.disk(cache_seed=312, cache_path_root=cache_dir) as cache:
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_response == warm_cache_response
        assert duration_with_warm_cache < duration_with_cold_cache
        assert os.path.exists(os.path.join(cache_dir, str(312)))
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(312)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test different cache seed.
    with Cache.disk(cache_seed=123, cache_path_root=cache_dir) as cache:
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time
        assert duration_with_warm_cache < duration_with_cold_cache
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(123)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))


if __name__ == "__main__":
    # test_aoai_chat_completion()
    # test_oai_tool_calling_extraction()
    # test_chat_completion()
    test_completion()
    # # test_cost()
    # test_usage_summary()
    # test_legacy_cache()
    # test_cache()
