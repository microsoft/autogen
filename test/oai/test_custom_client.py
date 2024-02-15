import pytest
from autogen import OpenAIWrapper
from autogen.oai import ModelClient
from typing import Dict

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False


def test_custom_model_client():
    TEST_COST = 20000000
    TEST_CUSTOM_RESPONSE = "This is a custom response."
    TEST_DEVICE = "cpu"
    TEST_LOCAL_MODEL_NAME = "local_model_name"
    TEST_OTHER_PARAMS_VAL = "other_params"
    TEST_MAX_LENGTH = 1000

    class CustomModel:
        def __init__(self, config: Dict, test_hook):
            self.test_hook = test_hook
            self.device = config["device"]
            self.model = config["model"]
            self.other_params = config["params"]["other_params"]
            self.max_length = config["params"]["max_length"]
            self.test_hook["called"] = True
            # set all params to test hook
            self.test_hook["device"] = self.device
            self.test_hook["model"] = self.model
            self.test_hook["other_params"] = self.other_params
            self.test_hook["max_length"] = self.max_length

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
            response.cost = TEST_COST
            return TEST_COST

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

    config_list = [
        {
            "model": TEST_LOCAL_MODEL_NAME,
            "model_client_cls": "CustomModel",
            "device": TEST_DEVICE,
            "params": {
                "max_length": TEST_MAX_LENGTH,
                "other_params": TEST_OTHER_PARAMS_VAL,
            },
        },
    ]

    test_hook = {"called": False}

    client = OpenAIWrapper(config_list=config_list)
    client.register_model_client(model_client_cls=CustomModel, test_hook=test_hook)

    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    assert response.choices[0].message.content == TEST_CUSTOM_RESPONSE
    assert response.cost == TEST_COST

    assert test_hook["called"]
    assert test_hook["device"] == TEST_DEVICE
    assert test_hook["model"] == TEST_LOCAL_MODEL_NAME
    assert test_hook["other_params"] == TEST_OTHER_PARAMS_VAL
    assert test_hook["max_length"] == TEST_MAX_LENGTH


def test_registering_with_wrong_class_name_raises_error():
    class CustomModel:
        def __init__(self, config: Dict):
            pass

        def create(self, params):
            return None

        def message_retrieval(self, response):
            return []

        def cost(self, response) -> float:
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

    config_list = [
        {
            "model": "local_model_name",
            "model_client_cls": "CustomModelWrongName",
        },
    ]
    client = OpenAIWrapper(config_list=config_list)

    with pytest.raises(ValueError):
        client.register_model_client(model_client_cls=CustomModel)


def test_not_all_clients_registered_raises_error():
    class CustomModel:
        def __init__(self, config: Dict):
            pass

        def create(self, params):
            return None

        def message_retrieval(self, response):
            return []

        def cost(self, response) -> float:
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

    config_list = [
        {
            "model": "local_model_name",
            "model_client_cls": "CustomModel",
            "device": "cpu",
            "params": {
                "max_length": 1000,
                "other_params": "other_params",
            },
        },
        {
            "model": "local_model_name_2",
            "model_client_cls": "CustomModel",
            "device": "cpu",
            "params": {
                "max_length": 1000,
                "other_params": "other_params",
            },
        },
    ]

    client = OpenAIWrapper(config_list=config_list)

    client.register_model_client(model_client_cls=CustomModel)

    with pytest.raises(RuntimeError):
        client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)


def test_registering_with_extra_config_args():
    class CustomModel:
        def __init__(self, config: Dict, test_hook):
            self.test_hook = test_hook
            self.test_hook["called"] = True

        def create(self, params):
            from types import SimpleNamespace

            response = SimpleNamespace()
            response.choices = []
            return response

        def message_retrieval(self, response):
            return []

        def cost(self, response) -> float:
            """Calculate the cost of the response."""
            return 0

        @staticmethod
        def get_usage(response) -> Dict:
            return {}

    config_list = [
        {
            "model": "local_model_name",
            "model_client_cls": "CustomModel",
            "device": "test_device",
        },
    ]

    test_hook = {"called": False}

    client = OpenAIWrapper(config_list=config_list, cache_seed=None)
    client.register_model_client(model_client_cls=CustomModel, test_hook=test_hook)
    client.create(messages=[{"role": "user", "content": "2+2="}])
    assert test_hook["called"]
