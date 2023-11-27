import asyncio
import autogen
import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST


@pytest.mark.asyncio
async def test_async_get_human_input():
    try:
        import openai
    except ImportError:
        return
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        max_consecutive_auto_reply=2,
        llm_config={"timeout": 600, "cache_seed": 41, "config_list": config_list, "temperature": 0},
    )

    user_proxy = autogen.UserProxyAgent(name="user", human_input_mode="ALWAYS", code_execution_config=False)

    async def custom_a_get_human_input(prompt):
        return "This is a test"

    user_proxy.a_get_human_input = custom_a_get_human_input

    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.a_check_termination_and_human_reply)

    await user_proxy.a_initiate_chat(assistant, clear_history=True, message="Hello.")


if __name__ == "__main__":
    test_async_get_human_input()
