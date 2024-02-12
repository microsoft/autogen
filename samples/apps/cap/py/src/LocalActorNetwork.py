from DebugLog import Debug, Warn
import zmq
from abc import ABC, abstractmethod

from ActorConnector import ActorConnector
from Broker import Broker
from CANConstants import Termination_Topic

class LocalActorNetwork():
    def __init__(self, name="Local Agent Network"):
        self.agents = {}
        self.name = name
        self._context = zmq.Context()
        self._broker = Broker(self._context)
        
    def __str__(self):
        return f"{self.name}"
        
    def register(self, agent):
        # Get agent's name and description and add to a dictionary so 
        # that we can look up the agent by name
        self.agents[agent.agent_name] = agent
        agent.start_recv_thread(self._context)
        Debug(f"Local_Agent_Network",f"{agent.agent_name} registered in the network.")

    def connect(self):
        self._broker.start()
        for agent in self.agents.values():
            agent.connect(self)
            
    def disconnect(self):
        for agent in self.agents.values():
            agent.disconnect(self)
        self._broker.stop()
    
    def agent_connector_by_topic(self, topic) -> ActorConnector:
        return ActorConnector(self._context, topic)        
    
    def lookup_agent(self, name) -> ActorConnector:
        agent = self.agents.get(name, None)
        if agent is None:
            Warn("Local_Agent_Network", f"{name}, not found in the network.")
            return None
        Debug("Local_Agent_Network", f"[{name}] found in the network.")
        return self.agent_connector_by_topic(name)

    def lookup_termination(self) -> ActorConnector:
        termination_topic = Termination_Topic
        return self.agent_connector_by_topic(termination_topic)

            
