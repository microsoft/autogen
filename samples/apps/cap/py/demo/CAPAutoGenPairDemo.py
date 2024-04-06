import time

from autogencap.ag_adapter.CAPPair import CAPPair
from autogencap.DebugLog import Info
from autogencap.LocalActorNetwork import LocalActorNetwork

from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


def cap_ag_pair_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )

    # Composable Agent Platform AutoGen Pair adapter
    network = LocalActorNetwork()

    pair = CAPPair(network, user_proxy, assistant)
    pair.initiate_chat("Plot a chart of MSFT daily closing prices for last 1 Month.")

    # Wait for the pair to finish
    try:
        while pair.running():
            # Hang out for a while and print out
            # status every now and then
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down.")

    network.disconnect()
    Info("App", "App Exit")
