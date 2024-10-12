import time

import autogencap.DebugLog as DebugLog
from autogencap.ag_adapter.CAPPair import CAPPair
from autogencap.DebugLog import ConsoleLogger, Info
from autogencap.runtime_factory import RuntimeFactory

from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


def cap_ag_pair_demo():
    DebugLog.LOGGER = ConsoleLogger(use_color=False)

    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )

    # Composable Agent Platform AutoGen Pair adapter
    ensemble = RuntimeFactory.get_runtime("ZMQ")

    pair = CAPPair(ensemble, user_proxy, assistant)
    user_cmd = "Plot a chart of MSFT daily closing prices for last 1 Month"
    print(f"Default: {user_cmd}")
    user_cmd = input("Enter a command: ") or user_cmd
    pair.initiate_chat(user_cmd)

    # Wait for the pair to finish
    try:
        while pair.running():
            # Hang out for a while and print out
            # status every now and then
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down.")

    ensemble.disconnect()
    Info("App", "App Exit")
