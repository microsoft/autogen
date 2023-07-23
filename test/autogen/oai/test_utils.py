import json
import os
from flaml import oai

KEY_LOC = "test/autogen"


def test_config_list_from_json():
    config_list = oai.config_list_gpt4_gpt35(key_file_path=KEY_LOC)
    json_file = os.path.join(KEY_LOC, "config_list_test.json")
    with open(json_file, "w") as f:
        json.dump(config_list, f, indent=4)
    config_list_1 = oai.config_list_from_json(json_file)
    assert config_list == config_list_1
    os.environ["config_list_test"] = json.dumps(config_list)
    config_list_2 = oai.config_list_from_json("config_list_test")
    assert config_list == config_list_2
    config_list_3 = oai.config_list_from_json(
        "OAI_CONFIG_LIST", file_location=KEY_LOC, filter_dict={"model": ["gpt4", "gpt-4-32k"]}
    )
    assert all(config.get("model") in ["gpt4", "gpt-4-32k"] for config in config_list_3)
    del os.environ["config_list_test"]
    os.remove(json_file)


def test_config_list_openai_aoai():
    config_list = oai.config_list_openai_aoai(key_file_path=KEY_LOC)
    assert all(config.get("api_type") in [None, "open_ai", "azure"] for config in config_list)


if __name__ == "__main__":
    test_config_list_from_json()
