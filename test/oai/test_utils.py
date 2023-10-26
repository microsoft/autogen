import os
import sys
import json
import pytest
import logging
import tempfile
from unittest import mock
import autogen  # noqa: E402

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"

sys.path.append("../../autogen")

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


@pytest.fixture
def mock_os_environ():
    with mock.patch.dict(os.environ, ENV_VARS):
        yield


def test_config_list_from_json():
    # Test the functionality for loading configurations from JSON file
    # and ensuring that the loaded configurations are as expected.
    config_list = autogen.config_list_gpt4_gpt35(key_file_path=KEY_LOC)
    json_file = os.path.join(KEY_LOC, "config_list_test.json")

    with open(json_file, "w") as f:
        json.dump(config_list, f, indent=4)

    config_list_1 = autogen.config_list_from_json(json_file)
    assert config_list == config_list_1

    os.environ["config_list_test"] = json.dumps(config_list)
    config_list_2 = autogen.config_list_from_json("config_list_test")
    assert config_list == config_list_2

    config_list_3 = autogen.config_list_from_json(
        OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"model": ["gpt4", "gpt-4-32k"]}
    )
    assert all(config.get("model") in ["gpt4", "gpt-4-32k"] for config in config_list_3)

    del os.environ["config_list_test"]
    os.remove(json_file)


def test_config_list_openai_aoai():
    # Testing the functionality for loading configurations for different API types
    # and ensuring the API types in the loaded configurations are as expected.
    config_list = autogen.config_list_openai_aoai(key_file_path=KEY_LOC)
    assert all(config.get("api_type") in [None, "open_ai", "azure"] for config in config_list)


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


if __name__ == "__main__":
    pytest.main()
