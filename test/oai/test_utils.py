import json
import os
import autogen
import pytest
import tempfile
from test_completion import KEY_LOC, OAI_CONFIG_LIST

from autogen.oai.openai_utils import config_list_from_dotenv


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
    # Test valid case
    config_list = config_list_from_dotenv(dotenv_file_path=dotenv_file)
    assert config_list, "Configuration list is empty in valid case"
    assert all(config["api_key"] == "SomeAPIKey" for config in config_list), "API Key mismatch in valid case"

    # Test invalid path case
    with pytest.raises(FileNotFoundError, match="The specified .env file invalid_path does not exist."):
        config_list_from_dotenv(dotenv_file_path="invalid_path")

    # Test no API key case
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp:
        temp.write("DIFFERENT_API_KEY=SomeAPIKey")
        temp.flush()
        with pytest.raises(
            ValueError, match=f"{autogen.api_key_env_var} not found. Please ensure path to .env file is correct."
        ):
            config_list_from_dotenv(dotenv_file_path=temp.name)

    # Test empty API key case
    with tempfile.NamedTemporaryFile(mode="w+", delete=True) as temp:
        temp.write("OPENAI_API_KEY=   ")
        temp.flush()
        with pytest.raises(
            ValueError, match=f"{autogen.api_key_env_var} not found. Please ensure path to .env file is correct."
        ):
            config_list_from_dotenv(dotenv_file_path=temp.name)


if __name__ == "__main__":
    test_config_list_from_json()
