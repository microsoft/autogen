from typing import List, Optional
from dataclasses import asdict
import autogen
from .datamodel import AgentFlowSpec, AgentWorkFlowConfig, Message
from .utils import get_skills_from_prompt, clear_folder
from datetime import datetime


class AutoGenWorkFlowManager:
    """
    AutoGenWorkFlowManager class to load agents from a provided configuration and run a chat between them
    """

    def __init__(
        self,
        config: AgentWorkFlowConfig,
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
    ) -> None:
        """
        Initializes the AutoGenFlow with agents specified in the config and optional
        message history.

        Args:
            config: The configuration settings for the sender and receiver agents.
            history: An optional list of previous messages to populate the agents' history.

        """
        self.work_dir = work_dir or "work_dir"
        if clear_work_dir:
            clear_folder(self.work_dir)

        self.sender = self.load(config.sender)
        self.receiver = self.load(config.receiver)
        self.agent_history = []

        if history:
            self.populate_history(history)

    def process_reply(self, recipient, messages, sender, config):
        if "callback" in config and config["callback"] is not None:
            callback = config["callback"]
            callback(sender, recipient, messages[-1])
        iteration = {
            "sender": sender.name,
            "recipient": recipient.name,
            "message": messages[-1],
            "timestamp": datetime.now().isoformat(),
        }
        self.agent_history.append(iteration)
        return False, None

    def _sanitize_history_message(self, message: str) -> str:
        """
        Sanitizes the message e.g. remove references to execution completed

        Args:
            message: The message to be sanitized.

        Returns:
            The sanitized message.
        """
        to_replace = ["execution succeeded", "exitcode"]
        for replace in to_replace:
            message = message.replace(replace, "")
        return message

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

    def sanitize_agent_spec(self, agent_spec: AgentFlowSpec) -> AgentFlowSpec:
        """
        Sanitizes the agent spec by setting loading defaults

        Args:
            config: The agent configuration to be sanitized.
            agent_type: The type of the agent.

        Returns:
            The sanitized agent configuration.
        """

        agent_spec.config.is_termination_msg = agent_spec.config.is_termination_msg or (
            lambda x: "TERMINATE" in x.get("content", "").rstrip()
        )
        skills_prompt = ""
        if agent_spec.skills:
            # get skill prompt, also write skills to a file named skills.py
            skills_prompt = get_skills_from_prompt(agent_spec.skills, self.work_dir)

        if agent_spec.type == "userproxy":
            code_execution_config = agent_spec.config.code_execution_config or {}
            code_execution_config["work_dir"] = self.work_dir
            agent_spec.config.code_execution_config = code_execution_config

        if agent_spec.type == "assistant":
            agent_spec.config.system_message = (
                autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE
                + "\n\n"
                + agent_spec.config.system_message
                + "\n\n"
                + skills_prompt
            )

        return agent_spec

    def load(self, agent_spec: AgentFlowSpec) -> autogen.Agent:
        """
        Loads an agent based on the provided agent specification.

        Args:
            agent_spec: The specification of the agent to be loaded.

        Returns:
            An instance of the loaded agent.
        """
        agent: autogen.Agent
        agent_spec = self.sanitize_agent_spec(agent_spec)
        if agent_spec.type == "assistant":
            agent = autogen.AssistantAgent(**asdict(agent_spec.config))
            agent.register_reply([autogen.Agent, None], reply_func=self.process_reply, config={"callback": None})
        elif agent_spec.type == "userproxy":
            agent = autogen.UserProxyAgent(**asdict(agent_spec.config))
            agent.register_reply([autogen.Agent, None], reply_func=self.process_reply, config={"callback": None})
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
