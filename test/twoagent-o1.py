from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

config_list = [{"api_type": "openai-o1", "model": "o1-mini"}]
assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent(
    "user_proxy", code_execution_config={"work_dir": "coding", "use_docker": False}
)  # IMPORTANT: set to True to run code in docker, recommended
user_proxy.initiate_chat(assistant, message="Save a chart of NVDA and TESLA stock price change YTD.")
