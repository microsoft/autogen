"""
This module initializes various pre-defined agents provided by the package.
BaseChatAgent is the base class for all agents in AgentChat.
"""

from ._assistant_agent import AssistantAgent
from ._base_chat_agent import BaseChatAgent
from ._code_executor_agent import CodeExecutorAgent
from ._message_filter_agent import MessageFilterAgent, MessageFilterConfig, PerSourceFilter
from ._society_of_mind_agent import SocietyOfMindAgent
from ._user_proxy_agent import UserProxyAgent

__all__ = [
    "BaseChatAgent",
    "AssistantAgent",
    "CodeExecutorAgent",
    "SocietyOfMindAgent",
    "UserProxyAgent",
    "MessageFilterAgent",
    "MessageFilterConfig",
    "PerSourceFilter",
]
