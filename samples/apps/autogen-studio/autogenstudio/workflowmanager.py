import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import autogen

from .datamodel import (
    Agent,
    AgentType,
    Message,
    SocketMessage,
)
from .utils import clear_folder, get_skills_from_prompt, load_code_execution_config, sanitize_model


class WorkflowManager:
    """
    AutoGenWorkFlowManager class to load agents from a provided configuration and run a chat between them
    """

    def __init__(
        self,
        workflow: Dict,
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
        send_message_function: Optional[callable] = None,
        connection_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the AutoGenFlow with agents specified in the config and optional
        message history.

        Args:
            config: The configuration settings for the sender and receiver agents.
            history: An optional list of previous messages to populate the agents' history.

        """
        # TODO - improved typing for workflow
        self.send_message_function = send_message_function
        self.connection_id = connection_id
        self.work_dir = work_dir or "work_dir"
        if clear_work_dir:
            clear_folder(self.work_dir)
        self.workflow = workflow
        self.sender = self.load(workflow.get("sender"))
        self.receiver = self.load(workflow.get("receiver"))
        self.agent_history = []

        if history:
            self._populate_history(history)

    def _serialize_agent(
        self,
        agent: Agent,
        mode: str = "python",
        include: Optional[List[str]] = {"config"},
        exclude: Optional[List[str]] = None,
    ) -> Dict:
        """ """
        # exclude = ["id","created_at", "updated_at","user_id","type"]
        exclude = exclude or {}
        include = include or {}
        if agent.type != AgentType.groupchat:
            exclude.update(
                {
                    "config": {
                        "admin_name",
                        "messages",
                        "max_round",
                        "admin_name",
                        "speaker_selection_method",
                        "allow_repeat_speaker",
                    }
                }
            )
        else:
            include = {
                "config": {
                    "admin_name",
                    "messages",
                    "max_round",
                    "admin_name",
                    "speaker_selection_method",
                    "allow_repeat_speaker",
                }
            }
        result = agent.model_dump(warnings=False, exclude=exclude, include=include, mode=mode)
        return result["config"]

    def process_message(
        self,
        sender: autogen.Agent,
        receiver: autogen.Agent,
        message: Dict,
        request_reply: bool = False,
        silent: bool = False,
        sender_type: str = "agent",
    ) -> None:
        """
        Processes the message and adds it to the agent history.

        Args:

            sender: The sender of the message.
            receiver: The receiver of the message.
            message: The message content.
            request_reply: If set to True, the message will be added to agent history.
            silent: determining verbosity.
            sender_type: The type of the sender of the message.
        """

        message = message if isinstance(message, dict) else {"content": message, "role": "user"}
        message_payload = {
            "recipient": receiver.name,
            "sender": sender.name,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "sender_type": sender_type,
            "connection_id": self.connection_id,
            "message_type": "agent_message",
        }
        # if the agent will respond to the message, or the message is sent by a groupchat agent. This avoids adding groupchat broadcast messages to the history (which are sent with request_reply=False), or when agent populated from history
        if request_reply is not False or sender_type == "groupchat":
            self.agent_history.append(message_payload)  # add to history
            if self.send_message_function:  # send over the message queue
                socket_msg = SocketMessage(
                    type="agent_message",
                    data=message_payload,
                    connection_id=self.connection_id,
                )
                self.send_message_function(socket_msg.dict())

    def _populate_history(self, history: List[Message]) -> None:
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
                    silent=True,
                )
            elif msg.role == "assistant":
                self.receiver.send(
                    msg.content,
                    self.sender,
                    request_reply=False,
                    silent=True,
                )

    def sanitize_agent(self, agent: Dict) -> Agent:
        """ """

        skills = agent.get("skills", [])
        agent = Agent.model_validate(agent)
        agent.config.is_termination_msg = agent.config.is_termination_msg or (
            lambda x: "TERMINATE" in x.get("content", "").rstrip()[-20:]
        )

        def get_default_system_message(agent_type: str) -> str:
            if agent_type == "assistant":
                return autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            else:
                return "You are a helpful AI Assistant."

        if agent.config.llm_config is not False:
            config_list = []
            for llm in agent.config.llm_config.config_list:
                # check if api_key is present either in llm or env variable
                if "api_key" not in llm and "OPENAI_API_KEY" not in os.environ:
                    error_message = f"api_key is not present in llm_config or OPENAI_API_KEY env variable for agent ** {agent.config.name}**. Update your workflow to provide an api_key to use the LLM."
                    raise ValueError(error_message)

                # only add key if value is not None
                sanitized_llm = sanitize_model(llm)
                config_list.append(sanitized_llm)
            agent.config.llm_config.config_list = config_list

        agent.config.code_execution_config = load_code_execution_config(
            agent.config.code_execution_config, work_dir=self.work_dir
        )

        if skills:
            skills_prompt = ""
            skills_prompt = get_skills_from_prompt(skills, self.work_dir)
            if agent.config.system_message:
                agent.config.system_message = agent.config.system_message + "\n\n" + skills_prompt
            else:
                agent.config.system_message = get_default_system_message(agent.type) + "\n\n" + skills_prompt
        return agent

    def load(self, agent: Any) -> autogen.Agent:
        """
        Loads an agent based on the provided agent specification.

        Args:
            agent_spec: The specification of the agent to be loaded.

        Returns:
            An instance of the loaded agent.
        """
        if not agent:
            raise ValueError(
                "An agent configuration in this workflow is empty. Please provide a valid agent configuration."
            )

        linked_agents = agent.get("agents", [])
        agent = self.sanitize_agent(agent)
        if agent.type == "groupchat":
            groupchat_agents = [self.load(agent) for agent in linked_agents]
            group_chat_config = self._serialize_agent(agent)
            group_chat_config["agents"] = groupchat_agents
            groupchat = autogen.GroupChat(**group_chat_config)
            agent = ExtendedGroupChatManager(
                groupchat=groupchat,
                message_processor=self.process_message,
                llm_config=agent.config.llm_config.model_dump(),
            )
            return agent

        else:
            if agent.type == "assistant":
                agent = ExtendedConversableAgent(
                    **self._serialize_agent(agent),
                    message_processor=self.process_message,
                )
            elif agent.type == "userproxy":
                agent = ExtendedConversableAgent(
                    **self._serialize_agent(agent),
                    message_processor=self.process_message,
                )
            else:
                raise ValueError(f"Unknown agent type: {agent.type}")
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


class ExtendedConversableAgent(autogen.ConversableAgent):
    def __init__(self, message_processor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_processor = message_processor

    def receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        if self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        super().receive(message, sender, request_reply, silent)


""


class ExtendedGroupChatManager(autogen.GroupChatManager):
    def __init__(self, message_processor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_processor = message_processor

    def receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        if self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="groupchat")
        super().receive(message, sender, request_reply, silent)
