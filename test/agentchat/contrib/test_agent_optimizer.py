import os
import sys

import pytest

import autogen
from autogen import AssistantAgent, UserProxyAgent
from autogen.agentchat.contrib.agent_optimizer import AgentOptimizer

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import reason, skip_openai
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

here = os.path.abspath(os.path.dirname(__file__))


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_record_conversation():
    problem = "Simplify $\\sqrt[3]{1+8} \\cdot \\sqrt[3]{1+\\sqrt[3]{8}}"

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    llm_config = {
        "config_list": config_list,
        "timeout": 60,
        "cache_seed": 42,
    }

    assistant = AssistantAgent("assistant", system_message="You are a helpful assistant.", llm_config=llm_config)
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config={
            "work_dir": f"{here}/test_agent_scripts",
            "use_docker": "python:3",
            "timeout": 60,
        },
        max_consecutive_auto_reply=3,
    )

    user_proxy.initiate_chat(assistant, message=problem)
    optimizer = AgentOptimizer(max_actions_per_step=3, llm_config=llm_config)
    optimizer.record_one_conversation(assistant.chat_messages_for_summary(user_proxy), is_satisfied=True)

    assert len(optimizer._trial_conversations_history) == 1
    assert len(optimizer._trial_conversations_performance) == 1
    assert optimizer._trial_conversations_performance[0]["Conversation 0"] == 1

    optimizer.reset_optimizer()
    assert len(optimizer._trial_conversations_history) == 0
    assert len(optimizer._trial_conversations_performance) == 0


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_step():
    problem = "Simplify $\\sqrt[3]{1+8} \\cdot \\sqrt[3]{1+\\sqrt[3]{8}}"

    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    llm_config = {
        "config_list": config_list,
        "timeout": 60,
        "cache_seed": 42,
    }
    assistant = AssistantAgent(
        "assistant",
        system_message="You are a helpful assistant.",
        llm_config=llm_config,
    )
    user_proxy = UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        code_execution_config={
            "work_dir": f"{here}/test_agent_scripts",
            "use_docker": "python:3",
            "timeout": 60,
        },
        max_consecutive_auto_reply=3,
    )

    optimizer = AgentOptimizer(max_actions_per_step=3, llm_config=llm_config, optimizer_model="gpt-4o-mini")
    user_proxy.initiate_chat(assistant, message=problem)
    optimizer.record_one_conversation(assistant.chat_messages_for_summary(user_proxy), is_satisfied=True)

    register_for_llm, register_for_exector = optimizer.step()

    print("-------------------------------------")
    print("register_for_llm:")
    print(register_for_llm)
    print("register_for_exector")
    print(register_for_exector)

    for item in register_for_llm:
        assistant.update_function_signature(**item)
    if len(register_for_exector.keys()) > 0:
        user_proxy.register_function(function_map=register_for_exector)

    print("-------------------------------------")
    print("Updated assistant.llm_config:")
    print(assistant.llm_config)
    print("Updated user_proxy._function_map:")
    print(user_proxy._function_map)
