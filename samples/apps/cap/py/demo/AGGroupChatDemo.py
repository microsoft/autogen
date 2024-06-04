from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent, config_list_from_json


def ag_groupchat_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    gpt4_config = {
        "cache_seed": 72,
        "temperature": 0,
        "config_list": config_list,
        "timeout": 120,
    }
    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        human_input_mode="TERMINATE",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )
    coder = AssistantAgent(name="Coder", llm_config=gpt4_config)
    pm = AssistantAgent(
        name="Product_manager",
        system_message="Creative in software product ideas.",
        llm_config=gpt4_config,
    )
    groupchat = GroupChat(agents=[user_proxy, coder, pm], messages=[], max_round=12)
    manager = GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
    user_proxy.initiate_chat(
        manager,
        message="Find a latest paper about gpt-4 on arxiv and find its potential applications in software.",
    )
