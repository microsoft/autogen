from typing import Union, List 
from dataclasses import asdict
import autogen  
from .datamodel import AgentFlowSpec, AgentConfig, Message


class AutoGenFlow(object):
    def __init__(self, sender: AgentConfig, receiver:  Union[AgentConfig, List[AgentConfig]], history: List[Message] = None):
        self.sender = self.load(sender)
        self.receiver = self.load(receiver)

        if history:
            # populate the agent message history 
            for msg in history:
                if msg["role"] == "user":
                    self.sender.send(
                        msg["content"],
                        self.receiver,
                        request_reply=False, 
                    )
                elif msg["role"] == "assistant":
                    self.receiver.send(
                        msg["content"],
                        self.sender,
                        request_reply=False, 
                    )
         
    
    def load(self, agent_spec:AgentFlowSpec):
        if agent_spec.type == "assistant":
            agent = autogen.AssistantAgent(**asdict(agent_spec.config))
        if agent_spec.type == "userproxy":
            agent = autogen.UserProxyAgent(**asdict(agent_spec.config))
        return agent
     
    def run(self, message:str, clear_history:bool=False):
        self.sender.initiate_chat(self.receiver,
                                        message=message,
                                        clear_history=clear_history,
                                        )
        