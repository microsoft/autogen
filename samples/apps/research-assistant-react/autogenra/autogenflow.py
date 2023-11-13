from typing import List, Optional
from dataclasses import asdict
import autogen
from .datamodel import AgentFlowSpec, FlowConfig, Message


class AutoGenFlow:
    """
    AutoGenFlow class to handle the interaction between a sender and a receiver agent
    based on the provided configuration and history of messages.
    """

    def __init__(self, config: FlowConfig, history: Optional[List[Message]] = None) -> None:
        """
        Initializes the AutoGenFlow with agents specified in the config and optional
        message history.

        Args:
            config: The configuration settings for the sender and receiver agents.
            history: An optional list of previous messages to populate the agents' history.
        """
        self.sender = self.load(config.sender)
        self.receiver = self.load(config.receiver)

        if history:
            self.populate_history(history)

    def populate_history(self, history: List[Message]) -> None:
        """
        Populates the agent message history from the provided list of messages.

        Args:
            history: A list of messages to populate the agents' history.
        """
        for msg in history:
            if isinstance(msg, dict):
                msg = Message(**msg)
            if msg.role == "user":
                self.sender.send(
                    msg.content,
                    self.receiver,
                    request_reply=False,
                )
            elif msg.role == "assistant":
                self.receiver.send(
                    msg.content,
                    self.sender,
                    request_reply=False,
                )

    def load(self, agent_spec: AgentFlowSpec) -> autogen.Agent:
        """
        Loads an agent based on the provided agent specification.

        Args:
            agent_spec: The specification of the agent to be loaded.

        Returns:
            An instance of the loaded agent.
        """
        agent: autogen.Agent
        if agent_spec.type == "assistant":
            agent = autogen.AssistantAgent(**asdict(agent_spec.config))
        elif agent_spec.type == "userproxy":
            agent = autogen.UserProxyAgent(**asdict(agent_spec.config))
        else:
            raise ValueError(f"Unknown agent type: {agent_spec.type}")
        return agent

    def run(self, message: str, clear_history: bool = False) -> None:
        """
        Initiates a chat between the sender and receiver agents with an initial message
        and an option to clear the history.

        Args:
            message: The initial message to start the chat.
            clear_history: If set to True, clears the chat history before initiating.
        """
        self.sender.initiate_chat(
            self.receiver,
            message=message,
            clear_history=clear_history,
        )
