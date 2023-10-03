from autogen import UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

# Create the agents.
assistant = TeachableAgent("assistant", llm_config={"config_list": config_list})
user_proxy = UserProxyAgent("user_proxy")

# Start the chat.
user_proxy.initiate_chat(assistant, message="Hi")
