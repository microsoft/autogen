import sys

import pytest

from autogen import AssistantAgent, UserProxyAgent

sys.path.append("samples/tools/finetuning")

from typing import Dict  # noqa: E402

from finetuning import update_model  # noqa: E402

sys.path.append("test")

TEST_CUSTOM_RESPONSE = "This is a custom response."
TEST_LOCAL_MODEL_NAME = "local_model_name"


def test_custom_model_client():
    TEST_LOSS = 0.5

    class UpdatableCustomModel:
        def __init__(self, config: Dict):
            self.model = config["model"]
            self.model_name = config["model"]

        def create(self, params):
            from types import SimpleNamespace

            response = SimpleNamespace()
            # need to follow Client.ClientResponseProtocol
            response.choices = []
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            choice.message.content = TEST_CUSTOM_RESPONSE
            response.choices.append(choice)
            response.model = self.model
            return response

        def message_retrieval(self, response):
            return [response.choices[0].message.content]

        def cost(self, response) -> float:
            """Calculate the cost of the response."""
            response.cost = 0
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

        def update_model(self, preference_data, messages, **kwargs):
            return {"loss": TEST_LOSS}

    config_list = [{"model": TEST_LOCAL_MODEL_NAME, "model_client_cls": "UpdatableCustomModel"}]

    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        human_input_mode="NEVER",
        llm_config={"config_list": config_list},
    )
    assistant.register_model_client(model_client_cls=UpdatableCustomModel)
    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        llm_config=False,
    )

    res = user_proxy.initiate_chat(assistant, message="2+2=", silent=True)
    response_content = res.summary

    assert response_content == TEST_CUSTOM_RESPONSE
    preference_data = [("this is what the response should have been like", response_content)]
    update_model_stats = update_model(assistant, preference_data, user_proxy)
    assert update_model_stats["update_stats"]["loss"] == TEST_LOSS


def test_update_model_without_client_raises_error():
    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=0,
        llm_config=False,
        code_execution_config=False,
    )

    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        llm_config=False,
    )

    user_proxy.initiate_chat(assistant, message="2+2=", silent=True)
    with pytest.raises(ValueError):
        update_model(assistant, [], user_proxy)


def test_custom_model_update_func_missing_raises_error():
    class UpdatableCustomModel:
        def __init__(self, config: Dict):
            self.model = config["model"]
            self.model_name = config["model"]

        def create(self, params):
            from types import SimpleNamespace

            response = SimpleNamespace()
            # need to follow Client.ClientResponseProtocol
            response.choices = []
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            choice.message.content = TEST_CUSTOM_RESPONSE
            response.choices.append(choice)
            response.model = self.model
            return response

        def message_retrieval(self, response):
            return [response.choices[0].message.content]

        def cost(self, response) -> float:
            """Calculate the cost of the response."""
            response.cost = 0
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

    config_list = [{"model": TEST_LOCAL_MODEL_NAME, "model_client_cls": "UpdatableCustomModel"}]

    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        human_input_mode="NEVER",
        llm_config={"config_list": config_list},
    )
    assistant.register_model_client(model_client_cls=UpdatableCustomModel)
    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        llm_config=False,
    )

    res = user_proxy.initiate_chat(assistant, message="2+2=", silent=True)
    response_content = res.summary

    assert response_content == TEST_CUSTOM_RESPONSE

    with pytest.raises(NotImplementedError):
        update_model(assistant, [], user_proxy)


def test_multiple_model_clients_raises_error():
    class UpdatableCustomModel:
        def __init__(self, config: Dict):
            self.model = config["model"]
            self.model_name = config["model"]

        def create(self, params):
            from types import SimpleNamespace

            response = SimpleNamespace()
            # need to follow Client.ClientResponseProtocol
            response.choices = []
            choice = SimpleNamespace()
            choice.message = SimpleNamespace()
            choice.message.content = TEST_CUSTOM_RESPONSE
            response.choices.append(choice)
            response.model = self.model
            return response

        def message_retrieval(self, response):
            return [response.choices[0].message.content]

        def cost(self, response) -> float:
            """Calculate the cost of the response."""
            response.cost = 0
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

        def update_model(self, preference_data, messages, **kwargs):
            return {}

    config_list = [
        {"model": TEST_LOCAL_MODEL_NAME, "model_client_cls": "UpdatableCustomModel"},
        {"model": TEST_LOCAL_MODEL_NAME, "model_client_cls": "UpdatableCustomModel"},
    ]

    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        human_input_mode="NEVER",
        llm_config={"config_list": config_list},
    )
    assistant.register_model_client(model_client_cls=UpdatableCustomModel)
    assistant.register_model_client(model_client_cls=UpdatableCustomModel)
    user_proxy = UserProxyAgent(
        "user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        llm_config=False,
    )

    user_proxy.initiate_chat(assistant, message="2+2=", silent=True)

    with pytest.raises(ValueError):
        update_model(assistant, [], user_proxy)
