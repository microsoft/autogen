#!/usr/bin/env python3 -m pytest

import json
import logging
import os
import tempfile
from typing import Dict, List
from unittest import mock
from unittest.mock import patch

import pytest
from conftest import MOCK_OPEN_AI_API_KEY

import autogen  # noqa: E402
from autogen.oai.openai_utils import DEFAULT_AZURE_API_VERSION, filter_config, is_valid_api_key

# Example environment variables
ENV_VARS = {
    "OPENAI_API_KEY": "sk-********************",
    "HUGGING_FACE_API_KEY": "**************************",
    "ANOTHER_API_KEY": "1234567890234567890",
}

# Example model to API key mappings
MODEL_API_KEY_MAP = {
    "gpt-4": "OPENAI_API_KEY",
    "gpt-3.5-turbo": {
        "api_key_env_var": "ANOTHER_API_KEY",
        "api_type": "aoai",
        "api_version": "v2",
        "base_url": "https://api.someotherapi.com",
    },
}

# Example filter dictionary
FILTER_DICT = {
    "model": {
        "gpt-4",
        "gpt-3.5-turbo",
    }
}

JSON_SAMPLE = """
[
    {
        "model": "gpt-3.5-turbo",
        "api_type": "openai",
        "tags": ["gpt35"]
    },
    {
        "model": "gpt-4",
        "api_type": "openai",
        "tags": ["gpt4"]
    },
    {
        "model": "gpt-35-turbo-v0301",
        "tags": ["gpt-3.5-turbo", "gpt35_turbo"],
        "api_key": "azureoaiapikey",
        "base_url": "https://deployment_name.openai.azure.com",
        "api_type": "azure",
        "api_version": "2024-02-01"
    },
    {
        "model": "gpt",
        "api_key": "not-needed",
        "base_url": "http://localhost:1234/v1"
    }
]
"""

JSON_SAMPLE_DICT = json.loads(JSON_SAMPLE)


FILTER_CONFIG_TEST = [
    {
        "filter_dict": {"tags": ["gpt35", "gpt4"]},
        "exclude": False,
        "expected": JSON_SAMPLE_DICT[0:2],
    },
    {
        "filter_dict": {"tags": ["gpt35", "gpt4"]},
        "exclude": True,
        "expected": JSON_SAMPLE_DICT[2:4],
    },
    {
        "filter_dict": {"api_type": "azure", "api_version": "2024-02-01"},
        "exclude": False,
        "expected": [JSON_SAMPLE_DICT[2]],
    },
]


def _compare_lists_of_dicts(list1: List[Dict], list2: List[Dict]) -> bool:
    dump1 = sorted(json.dumps(d, sort_keys=True) for d in list1)
    dump2 = sorted(json.dumps(d, sort_keys=True) for d in list2)
    return dump1 == dump2


@pytest.fixture
def mock_os_environ():
    with mock.patch.dict(os.environ, ENV_VARS):
        yield


@pytest.mark.parametrize("test_case", FILTER_CONFIG_TEST)
def test_filter_config(test_case):
    filter_dict = test_case["filter_dict"]
    exclude = test_case["exclude"]
    expected = test_case["expected"]

    config_list = filter_config(JSON_SAMPLE_DICT, filter_dict, exclude)

    assert _compare_lists_of_dicts(config_list, expected)


def test_config_list_from_json():
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp_file:
        json_data = json.loads(JSON_SAMPLE)
        tmp_file.write(JSON_SAMPLE)
        tmp_file.flush()
        config_list = autogen.config_list_from_json(tmp_file.name)

        assert len(config_list) == len(json_data)
        i = 0
        for config in config_list:
            assert isinstance(config, dict)
            for key in config:
                assert key in json_data[i]
                assert config[key] == json_data[i][key]
            i += 1

        os.environ["config_list_test"] = JSON_SAMPLE
        config_list_2 = autogen.config_list_from_json("config_list_test")
        assert config_list == config_list_2

        # Test: the env variable is set to a file path with folder name inside.
        config_list_3 = autogen.config_list_from_json(
            tmp_file.name, filter_dict={"model": ["gpt", "gpt-4", "gpt-4-32k"]}
        )
        assert all(config.get("model") in ["gpt-4", "gpt"] for config in config_list_3)

        del os.environ["config_list_test"]

        # Test: using the `file_location` parameter.
        config_list_4 = autogen.config_list_from_json(
            os.path.basename(tmp_file.name),
            file_location=os.path.dirname(tmp_file.name),
            filter_dict={"model": ["gpt4", "gpt-4-32k"]},
        )

        assert all(config.get("model") in ["gpt4", "gpt-4-32k"] for config in config_list_4)

        # Test: the env variable is set to a file path.
        fd, temp_name = tempfile.mkstemp()
        json.dump(config_list, os.fdopen(fd, "w+"), indent=4)
        os.environ["config_list_test"] = temp_name
        config_list_5 = autogen.config_list_from_json("config_list_test")
        assert config_list_5 == config_list_2

        del os.environ["config_list_test"]

    # Test that an error is thrown when the config list is missing
    with pytest.raises(FileNotFoundError):
        autogen.config_list_from_json("OAI_CONFIG_LIST.missing")


def test_config_list_openai_aoai():
    # Testing the functionality for loading configurations for different API types
    # and ensuring the API types in the loaded configurations are as expected.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create temporary files with sample data for keys and base URLs
        openai_key_file = os.path.join(temp_dir, "key_openai.txt")
        aoai_key_file = os.path.join(temp_dir, "key_aoai.txt")
        openai_base_file = os.path.join(temp_dir, "base_openai.txt")
        aoai_base_file = os.path.join(temp_dir, "base_aoai.txt")

        # Write sample data to the temporary files
        with open(openai_key_file, "w") as f:
            f.write("sk-testkeyopenai123\nsk-testkeyopenai456")
        with open(aoai_key_file, "w") as f:
            f.write("sk-testkeyaoai456")
        with open(openai_base_file, "w") as f:
            f.write("https://api.openai.com/v1\nhttps://api.openai.com/v1")
        with open(aoai_base_file, "w") as f:
            f.write("https://api.azure.com/v1")

        # Pass the temporary directory as a parameter to the function
        config_list = autogen.config_list_openai_aoai(key_file_path=temp_dir)
        assert len(config_list) == 3
        expected_config_list = [
            {"api_key": "sk-testkeyopenai123", "base_url": "https://api.openai.com/v1"},
            {"api_key": "sk-testkeyopenai456", "base_url": "https://api.openai.com/v1"},
            {
                "api_key": "sk-testkeyaoai456",
                "base_url": "https://api.azure.com/v1",
                "api_type": "azure",
                "api_version": DEFAULT_AZURE_API_VERSION,
            },
        ]
        assert config_list == expected_config_list


@patch(
    "os.environ",
    {
        "OPENAI_API_KEY": "test_openai_key",
        "OPENAI_API_BASE": "https://api.openai.com",
        "AZURE_OPENAI_API_KEY": "test_aoai_key",
        "AZURE_OPENAI_API_BASE": "https://api.azure.com",
    },
)
def test_config_list_openai_aoai_env_vars():
    # Test the config_list_openai_aoai function with environment variables set
    configs = autogen.oai.openai_utils.config_list_openai_aoai(key_file_path=None)
    assert len(configs) == 2
    assert {"api_key": "test_openai_key", "base_url": "https://api.openai.com"} in configs
    assert {
        "api_key": "test_aoai_key",
        "base_url": "https://api.azure.com",
        "api_type": "azure",
        "api_version": DEFAULT_AZURE_API_VERSION,
    } in configs


@patch(
    "os.environ",
    {
        "OPENAI_API_KEY": "test_openai_key\ntest_openai_key2",
        "OPENAI_API_BASE": "https://api.openai.com\nhttps://api.openai.com/v2",
        "AZURE_OPENAI_API_KEY": "test_aoai_key\ntest_aoai_key2",
        "AZURE_OPENAI_API_BASE": "https://api.azure.com\nhttps://api.azure.com/v2",
    },
)
def test_config_list_openai_aoai_env_vars_multi():
    # Test the config_list_openai_aoai function with multiple environment variable values (new line separated)
    configs = autogen.oai.openai_utils.config_list_openai_aoai()
    assert len(configs) == 4
    assert {"api_key": "test_openai_key", "base_url": "https://api.openai.com"} in configs
    assert {"api_key": "test_openai_key2", "base_url": "https://api.openai.com/v2"} in configs
    assert {
        "api_key": "test_aoai_key",
        "base_url": "https://api.azure.com",
        "api_type": "azure",
        "api_version": DEFAULT_AZURE_API_VERSION,
    } in configs
    assert {
        "api_key": "test_aoai_key2",
        "base_url": "https://api.azure.com/v2",
        "api_type": "azure",
        "api_version": DEFAULT_AZURE_API_VERSION,
    } in configs


def test_config_list_openai_aoai_file_not_found():
    with mock.patch.dict(os.environ, {}, clear=True):
        config_list = autogen.config_list_openai_aoai(key_file_path="non_existent_path")
        assert len(config_list) == 0


def test_config_list_from_dotenv(mock_os_environ, caplog):
    # Test with valid .env file
    fd, temp_name = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w+") as temp:
            temp.write("\n".join([f"{k}={v}" for k, v in ENV_VARS.items()]))
            temp.flush()
            # Use the updated config_list_from_dotenv function
            config_list = autogen.config_list_from_dotenv(dotenv_file_path=temp_name)

            # Ensure configurations are loaded and API keys match expected values
            assert config_list, "Config list is empty with default API keys"

            # Check that configurations only include models specified in the filter
            for config in config_list:
                assert config["model"] in FILTER_DICT["model"], f"Model {config['model']} not in filter"

            # Check the default API key for gpt-4 and gpt-3.5-turbo when model_api_key_map is None
            config_list = autogen.config_list_from_dotenv(dotenv_file_path=temp_name, model_api_key_map=None)

            expected_api_key = os.getenv("OPENAI_API_KEY")
            assert any(
                config["model"] == "gpt-4" and config["api_key"] == expected_api_key for config in config_list
            ), "Default gpt-4 configuration not found or incorrect"
            assert any(
                config["model"] == "gpt-3.5-turbo" and config["api_key"] == expected_api_key for config in config_list
            ), "Default gpt-3.5-turbo configuration not found or incorrect"
    finally:
        os.remove(temp_name)  # The file is deleted after using its name (to prevent windows build from breaking)

    # Test with missing dotenv file
    with caplog.at_level(logging.WARNING):
        config_list = autogen.config_list_from_dotenv(dotenv_file_path="non_existent_path")
        assert "The specified .env file non_existent_path does not exist." in caplog.text

    # Test with invalid API key
    ENV_VARS["ANOTHER_API_KEY"] = ""  # Removing ANOTHER_API_KEY value

    with caplog.at_level(logging.WARNING):
        config_list = autogen.config_list_from_dotenv()
        assert "No .env file found. Loading configurations from environment variables." in caplog.text
        # The function does not return an empty list if at least one configuration is loaded successfully
        assert config_list != [], "Config list is empty"

    # Test with no configurations loaded
    invalid_model_api_key_map = {
        "gpt-4": "INVALID_API_KEY",  # Simulate an environment var name that doesn't exist
    }
    with caplog.at_level(logging.ERROR):
        # Mocking `config_list_from_json` to return an empty list and raise an exception when called
        with mock.patch("autogen.config_list_from_json", return_value=[], side_effect=Exception("Mock called")):
            # Call the function with the invalid map
            config_list = autogen.config_list_from_dotenv(
                model_api_key_map=invalid_model_api_key_map,
                filter_dict={
                    "model": {
                        "gpt-4",
                    }
                },
            )

            # Assert that the configuration list is empty
            assert not config_list, "Expected no configurations to be loaded"

    # test for mixed validity in the keymap
    invalid_model_api_key_map = {
        "gpt-4": "INVALID_API_KEY",
        "gpt-3.5-turbo": "ANOTHER_API_KEY",  # valid according to the example configs
    }

    with caplog.at_level(logging.WARNING):
        # Call the function with the mixed validity map
        config_list = autogen.config_list_from_dotenv(model_api_key_map=invalid_model_api_key_map)
        assert config_list, "Expected configurations to be loaded"
        assert any(
            config["model"] == "gpt-3.5-turbo" for config in config_list
        ), "gpt-3.5-turbo configuration not found"
        assert all(
            config["model"] != "gpt-4" for config in config_list
        ), "gpt-4 configuration found, but was not expected"
        assert "API key not found or empty for model gpt-4" in caplog.text


def test_get_config_list():
    # Define a list of API keys and corresponding base URLs
    api_keys = ["key1", "key2", "key3"]
    base_urls = ["https://api.service1.com", "https://api.service2.com", "https://api.service3.com"]
    api_type = "openai"
    api_version = "v1"

    # Call the get_config_list function to get a list of configuration dictionaries
    config_list = autogen.get_config_list(api_keys, base_urls, api_type, api_version)

    # Check that the config_list is not empty
    assert config_list, "The config_list should not be empty."

    # Check that the config_list has the correct length
    assert len(config_list) == len(
        api_keys
    ), "The config_list should have the same number of items as the api_keys list."

    # Check that each config in the config_list has the correct structure and data
    for i, config in enumerate(config_list):
        assert config["api_key"] == api_keys[i], f"The api_key for config {i} is incorrect."
        assert config["base_url"] == base_urls[i], f"The base_url for config {i} is incorrect."
        assert config["api_type"] == api_type, f"The api_type for config {i} is incorrect."
        assert config["api_version"] == api_version, f"The api_version for config {i} is incorrect."

    # Test with mismatched lengths of api_keys and base_urls
    with pytest.raises(AssertionError) as exc_info:
        autogen.get_config_list(api_keys, base_urls[:2], api_type, api_version)
    assert str(exc_info.value) == "The length of api_keys must match the length of base_urls"

    # Test with empty api_keys
    with pytest.raises(AssertionError) as exc_info:
        autogen.get_config_list([], base_urls, api_type, api_version)
    assert str(exc_info.value) == "The length of api_keys must match the length of base_urls"

    # Test with None base_urls
    config_list_without_base = autogen.get_config_list(api_keys, None, api_type, api_version)
    assert all(
        "base_url" not in config for config in config_list_without_base
    ), "The configs should not have base_url when None is provided."

    # Test with empty string in api_keys
    api_keys_with_empty = ["key1", "", "key3"]
    config_list_with_empty_key = autogen.get_config_list(api_keys_with_empty, base_urls, api_type, api_version)
    assert len(config_list_with_empty_key) == 2, "The config_list should exclude configurations with empty api_keys."


def test_tags():
    config_list = json.loads(JSON_SAMPLE)

    target_list = filter_config(config_list, {"model": ["gpt-35-turbo-v0301"]})
    assert len(target_list) == 1

    list_1 = filter_config(config_list, {"tags": ["gpt35_turbo"]})
    assert len(list_1) == 1
    assert list_1[0] == target_list[0]

    list_2 = filter_config(config_list, {"tags": ["gpt-3.5-turbo"]})
    assert len(list_2) == 1
    assert list_2[0] == target_list[0]

    list_3 = filter_config(config_list, {"tags": ["gpt-3.5-turbo", "gpt35_turbo"]})
    assert len(list_3) == 1
    assert list_3[0] == target_list[0]

    # Will still match because there's a non-empty intersection
    list_4 = filter_config(config_list, {"tags": ["gpt-3.5-turbo", "does_not_exist"]})
    assert len(list_4) == 1
    assert list_4[0] == target_list[0]

    list_5 = filter_config(config_list, {"tags": ["does_not_exist"]})
    assert len(list_5) == 0


def test_is_valid_api_key():
    assert not is_valid_api_key("")
    assert not is_valid_api_key("sk-")
    assert not is_valid_api_key("SK-")
    assert not is_valid_api_key("sk-asajsdjsd2")
    assert not is_valid_api_key("FooBar")
    assert not is_valid_api_key("sk-asajsdjsd22372%23kjdfdfdf2329ffUUDSDS")
    assert is_valid_api_key("sk-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS")
    assert is_valid_api_key("sk-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS1212121221212sssXX")
    assert is_valid_api_key("sk-proj-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert is_valid_api_key("sk-0-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert is_valid_api_key("sk-aut0gen-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert is_valid_api_key("sk-aut0-gen-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert is_valid_api_key("sk-aut0--gen-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert not is_valid_api_key("sk-aut0-gen--asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert not is_valid_api_key("sk--aut0-gen-asajsdjsd22372X23kjdfdfdf2329ffUUDSDS12121212212")
    assert is_valid_api_key(MOCK_OPEN_AI_API_KEY)


if __name__ == "__main__":
    pytest.main()
