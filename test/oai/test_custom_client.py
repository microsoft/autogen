from autogen import OpenAIWrapper
from autogen.oai import Client
from typing import Dict


def test_custom_client():
    TEST_COST = 20000000
    TEST_CUSTOM_RESPONSE = "This is a custom response."
    TEST_DEVICE = "cpu"
    TEST_LOCAL_MODEL_NAME = "local_model_name"
    TEST_OTHER_PARAMS_VAL = "other_params"
    TEST_MAX_LENGTH = 1000

    class CustomClient(Client):
        def __init__(self, config: Dict, test_hook):
            self.test_hook = test_hook
            self.device = config["device"]
            self.model = config["model"]
            self.other_params = config["params"]["other_params"]
            self.max_length = config["params"]["max_length"]

        def update(self, config: Dict):
            self.test_hook["called"] = True
            # set all params to test hook
            self.test_hook["device"] = self.device
            self.test_hook["model"] = self.model
            self.test_hook["other_params"] = self.other_params
            self.test_hook["max_length"] = self.max_length

        def create(self, params):
            if params.get("stream", False) and "messages" in params and "functions" not in params:
                raise NotImplementedError("Custom Client does not support streaming or functions")
            else:
                from types import SimpleNamespace

                response = SimpleNamespace()
                # need to follow Client.ClientResponseProtocol
                response.choices = []
                choice = SimpleNamespace()
                choice.message = SimpleNamespace()
                choice.message.content = TEST_CUSTOM_RESPONSE
                choice.message.function_call = None
                response.choices.append(choice)
                return response

        def cost(self, response) -> float:
            """Calculate the cost of the response."""
            response.cost = TEST_COST
            return TEST_COST

    config_list = [
        {
            "model": TEST_LOCAL_MODEL_NAME,
            "device": TEST_DEVICE,
            "params": {
                "max_length": TEST_MAX_LENGTH,
                "other_params": TEST_OTHER_PARAMS_VAL,
            },
        },
    ]

    test_hook = {"called": False}
    config_list[0]["custom_client"] = CustomClient(config=config_list[0], test_hook=test_hook)

    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    assert response.choices[0].message.content == TEST_CUSTOM_RESPONSE
    assert response.choices[0].message.function_call is None
    assert response.cost == TEST_COST

    assert test_hook["called"]
    assert test_hook["device"] == TEST_DEVICE
    assert test_hook["model"] == TEST_LOCAL_MODEL_NAME
    assert test_hook["other_params"] == TEST_OTHER_PARAMS_VAL
    assert test_hook["max_length"] == TEST_MAX_LENGTH
