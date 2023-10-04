import os
import sys
import json
import pytest
import logging
import tempfile
from unittest import mock
from test_completion import KEY_LOC, OAI_CONFIG_LIST

sys.path.append("../../autogen")
import autogen  # noqa: E402

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
        "api_base": "https://api.someotherapi.com",
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
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp:
        temp.write("\n".join([f"{k}={v}" for k, v in ENV_VARS.items()]))
        temp.flush()

        config_list = autogen.config_list_from_dotenv(
            dotenv_file_path=temp.name, model_api_key_map=MODEL_API_KEY_MAP, filter_dict=FILTER_DICT
        )

        # Ensure configurations are loaded and API keys match expected values
        assert config_list, "Config list is empty"
        for config in config_list:
            api_key_info = MODEL_API_KEY_MAP[config["model"]]
            api_key_var_name = api_key_info if isinstance(api_key_info, str) else api_key_info["api_key_env_var"]
            assert config["api_key"] == ENV_VARS[api_key_var_name], "API Key mismatch in valid case"

    # Test with missing dotenv file
    with pytest.raises(FileNotFoundError, match=r"The specified \.env file .* does not exist\."):
        autogen.config_list_from_dotenv(dotenv_file_path="non_existent_path")

    # Test with invalid API key
    ENV_VARS["ANOTHER_API_KEY"] = ""  # Removing ANOTHER_API_KEY value

    with caplog.at_level(logging.WARNING):
        result = autogen.config_list_from_dotenv(model_api_key_map=MODEL_API_KEY_MAP)
        assert "No .env file found. Loading configurations from environment variables." in caplog.text
        # The function does not return an empty list if at least one configuration is loaded successfully
        assert result != [], "Config list is empty"

    # Test with no configurations loaded
    invalid_model_api_key_map = {
        "gpt-4": "INVALID_API_KEY",  # Simulate an environment var name that doesn't exist
    }
    with caplog.at_level(logging.ERROR):
        config_list = autogen.config_list_from_dotenv(model_api_key_map=invalid_model_api_key_map)
    assert "No configurations loaded." in caplog.text
    assert not config_list


if __name__ == "__main__":
    pytest.main()
