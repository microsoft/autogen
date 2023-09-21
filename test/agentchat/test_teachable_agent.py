import os

os.environ["OPENAI_API_KEY"] = ""

from autogen import UserProxyAgent
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

assistant = TeachableAgent("assistant")
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Hi")
