import time
from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent, config_list_from_json
from autogencap.DebugLog import Info
from autogencap.LocalActorNetwork import LocalActorNetwork
from autogencap.ag_adapter.AG2CAP import AG2CAP
from autogencap.ag_adapter.CAP2AG import CAP2AG

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

    # Composable Agent Network adapter

    network = LocalActorNetwork()
    user_proxy_cap2ag = CAP2AG(ag_agent=user_proxy, the_other_name="chat_manager", init_chat=True, self_recursive=False)

    coder_cap2ag = CAP2AG(ag_agent=coder, the_other_name="chat_manager", init_chat=False, self_recursive=False)

    pm_cap2ag = CAP2AG(ag_agent=pm, the_other_name="chat_manager", init_chat=False, self_recursive=False)
    network.register(user_proxy_cap2ag)
    network.register(coder_cap2ag)
    network.register(pm_cap2ag)

    user_proxy_ag2cap = AG2CAP(network, agent_name=user_proxy.name, agent_description=user_proxy.description)
    coder_ag2cap = AG2CAP(network, agent_name=coder.name, agent_description=coder.description)
    pm_ag2cap = AG2CAP(network, agent_name=pm.name, agent_description=pm.description)
    groupchat = GroupChat(agents=[user_proxy_ag2cap, coder_ag2cap, pm_ag2cap], messages=[], max_round=12)

    manager = GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

    manager_cap2ag = CAP2AG(ag_agent=manager, the_other_name=user_proxy.name, init_chat=False, self_recursive=True)
    network.register(manager_cap2ag)

    time.sleep(0.01)
    network.connect()
    time.sleep(0.01)
    user_proxy_conn = network.lookup_agent(user_proxy.name)
    time.sleep(0.01)
    user_proxy_conn.send_txt_msg(
        "Find a latest paper about gpt-4 on arxiv and find its potential applications in software."
    )

    while True:
        time.sleep(0.5)
        if not user_proxy_cap2ag.run and not coder_cap2ag.run and not pm_cap2ag.run and not manager_cap2ag.run:
            break

    network.disconnect()
    Info("App", "App Exit")