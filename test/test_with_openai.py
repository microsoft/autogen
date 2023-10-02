import autogen
import pytest
import sys

try:
    import openai

    skip = False
except ImportError:
    skip = True


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_function_call_groupchat():
    import random

    def get_random_number():
        return random.randint(0, 100)

    config_list_gpt4 = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
    )
    llm_config = {
        "config_list": config_list_gpt4,
        "seed": 42,
        "functions": [
            {
                "name": "get_random_number",
                "description": "Get a random number between 0 and 100",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ],
    }
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin that will execute function_calls.",
        function_map={"get_random_number": get_random_number},
        human_input_mode="NEVER",
    )
    coder = autogen.AssistantAgent(
        name="Player",
        system_message="You will can function `get_random_number` to get a random number. Stop only when you get at least 1 even number and 1 odd number. Reply TERMINATE to stop.",
        llm_config=llm_config,
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, coder], messages=[], max_round=7)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    user_proxy.initiate_chat(manager, message="Let's start the game!")


if __name__ == "__main__":
    test_function_call_groupchat()
