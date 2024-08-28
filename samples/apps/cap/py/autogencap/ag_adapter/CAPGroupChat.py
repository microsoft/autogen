from typing import List

from autogen import Agent, AssistantAgent, GroupChat
from autogencap.ag_adapter.AG2CAP import AG2CAP
from autogencap.ag_adapter.CAP2AG import CAP2AG

from ..actor_runtime import IRuntime


class CAPGroupChat(GroupChat):
    def __init__(
        self,
        agents: List[AssistantAgent],
        messages: List[str],
        max_round: int,
        chat_initiator: str,
        ensemble: IRuntime,
    ):
        self.chat_initiator: str = chat_initiator
        self._cap_network: IRuntime = ensemble
        self._cap_proxies: List[CAP2AG] = []
        self._ag_proxies: List[AG2CAP] = []
        self._ag_agents: List[Agent] = agents
        self._init_cap_proxies()
        self._init_ag_proxies()
        super().__init__(agents=self._ag_proxies, messages=messages, max_round=max_round)

    def _init_cap_proxies(self):
        for agent in self._ag_agents:
            init_chat = agent.name == self.chat_initiator
            cap2ag = CAP2AG(ag_agent=agent, the_other_name="chat_manager", init_chat=init_chat, self_recursive=False)
            self._cap_network.register(cap2ag)
            self._cap_proxies.append(cap2ag)

    def _init_ag_proxies(self):
        for agent in self._ag_agents:
            ag2cap = AG2CAP(self._cap_network, agent_name=agent.name, agent_description=agent.description)
            self._ag_proxies.append(ag2cap)

    def is_running(self) -> bool:
        return all(proxy.run for proxy in self._cap_proxies)
