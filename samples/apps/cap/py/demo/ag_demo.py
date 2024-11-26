from autogen import AssistantAgent, UserProxyAgent, config_list_from_json


def ag_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )
    user_proxy.initiate_chat(assistant, message="Plot a chart of MSFT daily closing prices for last 1 Month.")
