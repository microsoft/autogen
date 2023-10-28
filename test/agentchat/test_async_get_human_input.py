import asyncio
import autogen
import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

async def test_stream():
    try:
        import openai
    except ImportError:
        return
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "request_timeout": 600,
            "seed": 41,
            "config_list": config_list,
            "temperature": 0
        }
    )

    user_proxy = autogen.UserProxyAgent(
        name="user",
        human_input_mode="ALWAYS",
        max_consecutive_auto_reply=1,
        code_execution_config=False,
        default_auto_reply=None
    )
    user_proxy._reply_func_list = []
    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_oai_reply)
    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_code_execution_reply)
    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_function_call_reply)
    user_proxy.register_reply([autogen.Agent, None], autogen.ConversableAgent.a_check_termination_and_human_reply)

    await user_proxy.a_initiate_chat(
        assistant,
        message="""Hello."""
    )

if __name__ == "__main__":
    asyncio.run(test_stream())
