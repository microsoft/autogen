import time
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from autogencap.DebugLog import Info
from autogencap.LocalActorNetwork import LocalActorNetwork
from autogencap.ag_adapter.CAP2AG import CAP2AG

def cap_ag_pair_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )

    # Composable Agent Network adapter

    network = LocalActorNetwork()
    user_proxy_adptr = CAP2AG(ag_agent=user_proxy, the_other_name="assistant", init_chat=True, self_recursive=True)
    assistant_adptr = CAP2AG(ag_agent=assistant, the_other_name="user_proxy", init_chat=False, self_recursive=True)

    network.register(user_proxy_adptr)
    network.register(assistant_adptr)
    network.connect()

    # Send a message to the user_proxy
    user_proxy = network.lookup_agent("user_proxy")
    user_proxy.send_txt_msg("Plot a chart of MSFT daily closing prices for last 1 Month.")

    # Hang around for a while
    while True:
        time.sleep(0.5)
        if not user_proxy_adptr.run and not assistant_adptr.run:
            break
    network.disconnect()
    Info("App", "App Exit")