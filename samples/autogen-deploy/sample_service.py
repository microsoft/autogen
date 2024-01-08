from celery import Celery
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from autogen_deploy import CeleryAgent

config_list = config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
    },
)

assistant = AssistantAgent(
    name="assistant",
    llm_config={
        "config_list": config_list,
    },
)
user_proxy = UserProxyAgent(
    "user_proxy",
    code_execution_config={"work_dir": "coding", "use_docker": False},
    human_input_mode="NEVER",
)

app = Celery("autogen_deploy", backend="rpc://", broker="pyamqp://guest@localhost//")
assistant = CeleryAgent(app, assistant)
user_proxy = CeleryAgent(app, user_proxy)
