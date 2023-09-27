from autogen import UserProxyAgent
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

assistant = TeachableAgent("assistant")
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Hi")
