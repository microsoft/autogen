import time

from autogen import ConversableAgent

from ..DebugLog import Info, Warn
from .CAP2AG import CAP2AG


class Agent:
    def __init__(self, agent: ConversableAgent, counter_party_name="user_proxy", init_chat=False):
        self._agent = agent
        self._the_other_name = counter_party_name
        self._agent_adptr = CAP2AG(
            ag_agent=self._agent, the_other_name=self._the_other_name, init_chat=init_chat, self_recursive=True
        )

    def register(self, network):
        Info("Agent", f"Running Standalone {self._agent.name}")
        network.register(self._agent_adptr)

    def running(self):
        return self._agent_adptr.run
