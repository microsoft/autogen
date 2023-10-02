import sys
import json
import os
import pytest
import tempfile
from test_completion import KEY_LOC, OAI_CONFIG_LIST

sys.path.append("../../autogen")
import autogen  # noqa: E402


def test_config_list_from_json():
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
    config_list = autogen.config_list_openai_aoai(key_file_path=KEY_LOC)
    assert all(config.get("api_type") in [None, "open_ai", "azure"] for config in config_list)


@pytest.fixture
def dotenv_file():
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp:
        temp.write("OPENAI_API_KEY=SomeAPIKey")
        temp.flush()
        yield temp.name


def test_config_list_from_dotenv(dotenv_file):
    api_key_env_var = "OPENAI_API_KEY"
    # Test valid case
    config_list = autogen.config_list_from_dotenv(dotenv_file_path=dotenv_file)
    assert config_list, "Configuration list is empty in valid case"
    assert all(config["api_key"] == "SomeAPIKey" for config in config_list), "API Key mismatch in valid case"

    # Test invalid path case
    with pytest.raises(FileNotFoundError, match="The specified .env file invalid_path does not exist."):
        autogen.config_list_from_dotenv(dotenv_file_path="invalid_path")

    # Test no API key case
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp:
        temp.write("DIFFERENT_API_KEY=SomeAPIKey")
        temp.flush()

        # Remove the OPENAI_API_KEY from environment variables if it exists
        original_api_key = os.environ.pop(api_key_env_var, None)

        try:
            # Explicitly check for ValueError due to missing API key
            with pytest.raises(
                ValueError, match=f"{api_key_env_var} not found or empty. Please ensure path to .env file is correct."
            ):
                autogen.config_list_from_dotenv(dotenv_file_path=temp.name)
        finally:
            # Restore the original OPENAI_API_KEY in environment variables after the test
            if original_api_key is not None:
                os.environ["OPENAI_API_KEY"] = original_api_key


if __name__ == "__main__":
    test_config_list_from_json()
