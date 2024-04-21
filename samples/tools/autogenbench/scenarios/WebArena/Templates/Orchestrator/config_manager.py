import os
from typing import Optional, List, Dict

import autogen


class ConfigManager:

    DEFAULT_LLM_MODEL = "gpt-4-turbo"
    DEFAULT_MLM_MODEL = "gpt-4-1106-vision-preview"
    DEFAULT_TIMEOUT = 300

    def __init__(self):
        self.llm_config = None
        self.client = None

        self.mlm_config = None
        self.mlm_client = None

        self.bing_api_key = None

    def _get_config_list(self, config_path_or_env: Optional[str] = None) -> List[Dict[str, str]]:
        config_list = None

        try:
            config_list = autogen.config_list_from_json(config_path_or_env)
        except Exception as e:  # config list may not be available
            api_key = os.environ.get("OPENAI_API_KEY", None)
            if api_key is None:
                raise Exception("No config list or OPENAI_API_KEY found", e)

            config_list = [
                {"model": self.DEFAULT_LLM_MODEL, "api_key": api_key, "tags": ["llm"]},
                {"model": self.DEFAULT_MLM_MODEL, "api_key": api_key, "tags": ["mlm"]},
            ]
        return config_list

    def _get_bing_api_key(self) -> str:
        bing_api_key = os.environ.get("BING_API_KEY", None)
        if bing_api_key is None:
            raise Exception("Please set BING_API_KEY environment variable.")
        return bing_api_key

    def initialize(self, config_path_or_env: Optional[str] = "OAI_CONFIG_LIST") -> None:

        config_list = self._get_config_list(config_path_or_env)

        llm_config_list = autogen.filter_config(config_list, {"tags": ["llm"]})
        assert len(llm_config_list) > 0, "No API key with 'llm' tag found in config list."

        mlm_config_list = autogen.filter_config(config_list, {"tags": ["mlm"]})
        assert len(mlm_config_list) > 0, "No API key with 'mlm' tag found in config list."

        self.llm_config = {"config_list": llm_config_list, "timeout": self.DEFAULT_TIMEOUT, "temperature": 0.1}

        self.mlm_config = {"config_list": mlm_config_list, "timeout": self.DEFAULT_TIMEOUT, "temperature": 0.1}

        self.client = autogen.OpenAIWrapper(**self.llm_config)
        self.mlm_client = autogen.OpenAIWrapper(**self.mlm_config)

        self.bing_api_key = self._get_bing_api_key()
