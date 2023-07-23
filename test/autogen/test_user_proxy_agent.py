from flaml import oai
from flaml.autogen.agent import AIUserProxyAgent, AssistantAgent
import pytest
import sys

KEY_LOC = "test/autogen"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows",
)
def test_ai_user_proxy_agent():
    try:
        import openai
    except ImportError:
        return

    conversations = {}
    oai.ChatCompletion.start_logging(conversations)

    config_list = oai.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        request_timeout=600,
        seed=42,
        config_list=config_list,
    )

    ai_user_proxy = AIUserProxyAgent(
        name="ai_user",
        human_input_mode="NEVER",
        config_list=config_list,
        max_consecutive_auto_reply=2,
        code_execution_config=False,
        # In the system message the "user" always refers to ther other agent.
        system_message="You ask a user for help. You check the answer from the user and provide feedback.",
    )
    assistant.reset()

    math_problem = "$x^3=125$. What is x?"
    ai_user_proxy.initiate_chat(
        assistant,
        message=math_problem,
    )
    print(conversations)


if __name__ == "__main__":
    test_ai_user_proxy_agent()
