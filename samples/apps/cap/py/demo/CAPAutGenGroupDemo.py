from autogencap.ag_adapter.CAPGroupChat import CAPGroupChat
from autogencap.ag_adapter.CAPGroupChatManager import CAPGroupChatManager
from autogencap.DebugLog import Info
from autogencap.runtime_factory import RuntimeFactory

from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


def cap_ag_group_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    gpt4_config = {
        "cache_seed": 73,
        "temperature": 0,
        "config_list": config_list,
        "timeout": 120,
    }
    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        human_input_mode="TERMINATE",
    )
    coder = AssistantAgent(name="Coder", llm_config=gpt4_config)
    pm = AssistantAgent(
        name="Product_manager",
        system_message="Creative in software product ideas.",
        llm_config=gpt4_config,
    )
    ensemble = RuntimeFactory.get_runtime("ZMQ")
    cap_groupchat = CAPGroupChat(
        agents=[user_proxy, coder, pm], messages=[], max_round=12, ensemble=ensemble, chat_initiator=user_proxy.name
    )
    manager = CAPGroupChatManager(groupchat=cap_groupchat, llm_config=gpt4_config, network=ensemble)
    manager.initiate_chat("Find a latest paper about gpt-4 on arxiv and find its potential applications in software.")
    ensemble.disconnect()
    Info("App", "App Exit")
