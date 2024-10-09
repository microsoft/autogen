import json
import os
import time
from datetime import datetime
from typing import Any, Coroutine, Dict, List, Optional, Union

import autogen

from .datamodel import (
    Agent,
    AgentType,
    CodeExecutionConfigTypes,
    Message,
    SocketMessage,
    Workflow,
    WorkFlowSummaryMethod,
    WorkFlowType,
)
from .utils import (
    clear_folder,
    find_key_value,
    get_modified_files,
    get_skills_prompt,
    load_code_execution_config,
    sanitize_model,
    save_skills_to_file,
    summarize_chat_history,
)


class AutoWorkflowManager:
    """
    WorkflowManager class to load agents from a provided configuration and run a chat between them.
    """

    def __init__(
        self,
        workflow: Union[Dict, str],
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
        send_message_function: Optional[callable] = None,
        a_send_message_function: Optional[Coroutine] = None,
        a_human_input_function: Optional[callable] = None,
        a_human_input_timeout: Optional[int] = 60,
        connection_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the WorkflowManager with agents specified in the config and optional message history.

        Args:
            workflow (Union[Dict, str]): The workflow configuration. This can be a dictionary or a string which is a path to a JSON file.
            history (Optional[List[Message]]): The message history.
            work_dir (str): The working directory.
            clear_work_dir (bool): If set to True, clears the working directory.
            send_message_function (Optional[callable]): The function to send messages.
            a_send_message_function (Optional[Coroutine]): Async coroutine to send messages.
            a_human_input_function (Optional[callable]): Async coroutine to prompt the user for input.
            a_human_input_timeout (Optional[int]): A time (in seconds) to wait for user input.  After this time, the a_human_input_function will timeout and end the conversation.
            connection_id (Optional[str]): The connection identifier.
        """
        if isinstance(workflow, str):
            if os.path.isfile(workflow):
                with open(workflow, "r") as file:
                    self.workflow = json.load(file)
            else:
                raise FileNotFoundError(f"The file {workflow} does not exist.")
        elif isinstance(workflow, dict):
            self.workflow = workflow
        else:
            raise ValueError("The 'workflow' parameter should be either a dictionary or a valid JSON file path")

        # TODO - improved typing for workflow
        self.workflow_skills = []
        self.send_message_function = send_message_function
        self.a_send_message_function = a_send_message_function
        self.a_human_input_function = a_human_input_function
        self.a_human_input_timeout = a_human_input_timeout
        self.connection_id = connection_id
        self.work_dir = work_dir or "work_dir"
        self.code_executor_pool = {
            CodeExecutionConfigTypes.local: load_code_execution_config(
                CodeExecutionConfigTypes.local, work_dir=self.work_dir
            ),
            CodeExecutionConfigTypes.docker: load_code_execution_config(
                CodeExecutionConfigTypes.docker, work_dir=self.work_dir
            ),
        }
        if clear_work_dir:
            clear_folder(self.work_dir)
        self.agent_history = []
        self.history = history or []
        self.sender = None
        self.receiver = None

    def _run_workflow(self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False) -> None:
        """
        Runs the workflow based on the provided configuration.

        Args:
            message: The initial message to start the chat.
            history: A list of messages to populate the agents' history.
            clear_history: If set to True, clears the chat history before initiating.

        """
        for agent in self.workflow.get("agents", []):
            if agent.get("link").get("agent_type") == "sender":
                self.sender = self.load(agent.get("agent"))
            elif agent.get("link").get("agent_type") == "receiver":
                self.receiver = self.load(agent.get("agent"))
        if self.sender and self.receiver:
            # save all agent skills to skills.py
            save_skills_to_file(self.workflow_skills, self.work_dir)
            if history:
                self._populate_history(history)
            self.sender.initiate_chat(
                self.receiver,
                message=message,
                clear_history=clear_history,
            )
        else:
            raise ValueError("Sender and receiver agents are not defined in the workflow configuration.")

    async def _a_run_workflow(
        self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False
    ) -> None:
        """
        Asynchronously runs the workflow based on the provided configuration.

        Args:
            message: The initial message to start the chat.
            history: A list of messages to populate the agents' history.
            clear_history: If set to True, clears the chat history before initiating.

        """
        for agent in self.workflow.get("agents", []):
            if agent.get("link").get("agent_type") == "sender":
                self.sender = self.load(agent.get("agent"))
            elif agent.get("link").get("agent_type") == "receiver":
                self.receiver = self.load(agent.get("agent"))
        if self.sender and self.receiver:
            # save all agent skills to skills.py
            save_skills_to_file(self.workflow_skills, self.work_dir)
            if history:
                self._populate_history(history)
            await self.sender.a_initiate_chat(
                self.receiver,
                message=message,
                clear_history=clear_history,
            )
        else:
            raise ValueError("Sender and receiver agents are not defined in the workflow configuration.")

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
        # if the agent will respond to the message, or the message is sent by a groupchat agent.
        # This avoids adding groupchat broadcast messages to the history (which are sent with request_reply=False),
        # or when agent populated from history
        if request_reply is not False or sender_type == "groupchat":
            self.agent_history.append(message_payload)  # add to history
            if self.send_message_function:  # send over the message queue
                socket_msg = SocketMessage(
                    type="agent_message",
                    data=message_payload,
                    connection_id=self.connection_id,
                )
                self.send_message_function(socket_msg.dict())

    async def a_process_message(
        self,
        sender: autogen.Agent,
        receiver: autogen.Agent,
        message: Dict,
        request_reply: bool = False,
        silent: bool = False,
        sender_type: str = "agent",
    ) -> None:
        """
        Asynchronously processes the message and adds it to the agent history.

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
        # if the agent will respond to the message, or the message is sent by a groupchat agent.
        # This avoids adding groupchat broadcast messages to the history (which are sent with request_reply=False),
        # or when agent populated from history
        if request_reply is not False or sender_type == "groupchat":
            self.agent_history.append(message_payload)  # add to history
            socket_msg = SocketMessage(
                type="agent_message",
                data=message_payload,
                connection_id=self.connection_id,
            )
            if self.a_send_message_function:  # send over the message queue
                await self.a_send_message_function(socket_msg.dict())
            elif self.send_message_function:  # send over the message queue
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

        # When human input mode is not NEVER and no model is attached, the ui is passing bogus llm_config.
        configured_models = agent.get("models")
        if not configured_models or len(configured_models) == 0:
            agent["config"]["llm_config"] = False

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

        agent.config.code_execution_config = self.code_executor_pool.get(agent.config.code_execution_config, False)

        if skills:
            for skill in skills:
                self.workflow_skills.append(skill)
            skills_prompt = ""
            skills_prompt = get_skills_prompt(skills, self.work_dir)
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
                a_message_processor=self.a_process_message,
                a_human_input_function=self.a_human_input_function,
                a_human_input_timeout=self.a_human_input_timeout,
                connection_id=self.connection_id,
                llm_config=agent.config.llm_config.model_dump(),
            )
            return agent

        else:
            if agent.type == "assistant":
                agent = ExtendedConversableAgent(
                    **self._serialize_agent(agent),
                    message_processor=self.process_message,
                    a_message_processor=self.a_process_message,
                    a_human_input_function=self.a_human_input_function,
                    a_human_input_timeout=self.a_human_input_timeout,
                    connection_id=self.connection_id,
                )
            elif agent.type == "userproxy":
                agent = ExtendedConversableAgent(
                    **self._serialize_agent(agent),
                    message_processor=self.process_message,
                    a_message_processor=self.a_process_message,
                    a_human_input_function=self.a_human_input_function,
                    a_human_input_timeout=self.a_human_input_timeout,
                    connection_id=self.connection_id,
                )
            else:
                raise ValueError(f"Unknown agent type: {agent.type}")
            return agent

    def _generate_output(
        self,
        message_text: str,
        summary_method: str,
    ) -> str:
        """
        Generates the output response based on the workflow configuration and agent history.

        :param message_text: The text of the incoming message.
        :param flow: An instance of `WorkflowManager`.
        :param flow_config: An instance of `AgentWorkFlowConfig`.
        :return: The output response as a string.
        """

        output = ""
        if summary_method == WorkFlowSummaryMethod.last:
            (self.agent_history)
            last_message = self.agent_history[-1]["message"]["content"] if self.agent_history else ""
            output = last_message
        elif summary_method == WorkFlowSummaryMethod.llm:
            client = self.receiver.client
            if self.connection_id:
                status_message = SocketMessage(
                    type="agent_status",
                    data={
                        "status": "summarizing",
                        "message": "Summarizing agent dialogue",
                    },
                    connection_id=self.connection_id,
                )
                self.send_message_function(status_message.model_dump(mode="json"))
            output = summarize_chat_history(
                task=message_text,
                messages=self.agent_history,
                client=client,
            )

        elif summary_method == "none":
            output = ""
        return output

    def _get_agent_usage(self, agent: autogen.Agent):
        final_usage = []
        default_usage = {"total_cost": 0, "total_tokens": 0}
        agent_usage = agent.client.total_usage_summary if agent.client else default_usage
        agent_usage = {
            "agent": agent.name,
            "total_cost": find_key_value(agent_usage, "total_cost") or 0,
            "total_tokens": find_key_value(agent_usage, "total_tokens") or 0,
        }
        final_usage.append(agent_usage)

        if type(agent) == ExtendedGroupChatManager:
            print("groupchat found, processing", len(agent.groupchat.agents))
            for agent in agent.groupchat.agents:
                agent_usage = agent.client.total_usage_summary if agent.client else default_usage or default_usage
                agent_usage = {
                    "agent": agent.name,
                    "total_cost": find_key_value(agent_usage, "total_cost") or 0,
                    "total_tokens": find_key_value(agent_usage, "total_tokens") or 0,
                }
                final_usage.append(agent_usage)
        return final_usage

    def _get_usage_summary(self):
        sender_usage = self._get_agent_usage(self.sender)
        receiver_usage = self._get_agent_usage(self.receiver)

        all_usage = []
        all_usage.extend(sender_usage)
        all_usage.extend(receiver_usage)
        # all_usage = [sender_usage, receiver_usage]
        return all_usage

    def run(self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False) -> Message:
        """
        Initiates a chat between the sender and receiver agents with an initial message
        and an option to clear the history.

        Args:
            message: The initial message to start the chat.
            clear_history: If set to True, clears the chat history before initiating.
        """

        start_time = time.time()
        self._run_workflow(message=message, history=history, clear_history=clear_history)
        end_time = time.time()

        output = self._generate_output(message, self.workflow.get("summary_method", "last"))

        usage = self._get_usage_summary()
        # print("usage", usage)

        result_message = Message(
            content=output,
            role="assistant",
            meta={
                "messages": self.agent_history,
                "summary_method": self.workflow.get("summary_method", "last"),
                "time": end_time - start_time,
                "files": get_modified_files(start_time, end_time, source_dir=self.work_dir),
                "usage": usage,
            },
        )
        return result_message

    async def a_run(
        self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False
    ) -> Message:
        """
        Asynchronously initiates a chat between the sender and receiver agents with an initial message
        and an option to clear the history.

        Args:
            message: The initial message to start the chat.
            clear_history: If set to True, clears the chat history before initiating.
        """

        start_time = time.time()
        await self._a_run_workflow(message=message, history=history, clear_history=clear_history)
        end_time = time.time()

        output = self._generate_output(message, self.workflow.get("summary_method", "last"))

        usage = self._get_usage_summary()
        # print("usage", usage)

        result_message = Message(
            content=output,
            role="assistant",
            meta={
                "messages": self.agent_history,
                "summary_method": self.workflow.get("summary_method", "last"),
                "time": end_time - start_time,
                "files": get_modified_files(start_time, end_time, source_dir=self.work_dir),
                "usage": usage,
            },
        )
        return result_message


class SequentialWorkflowManager:
    """
    WorkflowManager class to load agents from a provided configuration and run a chat between them sequentially.
    """

    def __init__(
        self,
        workflow: Union[Dict, str],
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
        send_message_function: Optional[callable] = None,
        a_send_message_function: Optional[Coroutine] = None,
        a_human_input_function: Optional[callable] = None,
        a_human_input_timeout: Optional[int] = 60,
        connection_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the WorkflowManager with agents specified in the config and optional message history.

        Args:
            workflow (Union[Dict, str]): The workflow configuration. This can be a dictionary or a string which is a path to a JSON file.
            history (Optional[List[Message]]): The message history.
            work_dir (str): The working directory.
            clear_work_dir (bool): If set to True, clears the working directory.
            send_message_function (Optional[callable]): The function to send messages.
            a_send_message_function (Optional[Coroutine]): Async coroutine to send messages.
            a_human_input_function (Optional[callable]): Async coroutine to prompt for human input.
            a_human_input_timeout (Optional[int]): A time (in seconds) to wait for user input.  After this time, the a_human_input_function will timeout and end the conversation.
            connection_id (Optional[str]): The connection identifier.
        """
        if isinstance(workflow, str):
            if os.path.isfile(workflow):
                with open(workflow, "r") as file:
                    self.workflow = json.load(file)
            else:
                raise FileNotFoundError(f"The file {workflow} does not exist.")
        elif isinstance(workflow, dict):
            self.workflow = workflow
        else:
            raise ValueError("The 'workflow' parameter should be either a dictionary or a valid JSON file path")

        # TODO - improved typing for workflow
        self.send_message_function = send_message_function
        self.a_send_message_function = a_send_message_function
        self.a_human_input_function = a_human_input_function
        self.a_human_input_timeout = a_human_input_timeout
        self.connection_id = connection_id
        self.work_dir = work_dir or "work_dir"
        if clear_work_dir:
            clear_folder(self.work_dir)
        self.agent_history = []
        self.history = history or []
        self.sender = None
        self.receiver = None
        self.model_client = None

    def _run_workflow(self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False) -> None:
        """
        Runs the workflow based on the provided configuration.

        Args:
            message: The initial message to start the chat.
            history: A list of messages to populate the agents' history.
            clear_history: If set to True, clears the chat history before initiating.

        """
        user_proxy = {
            "config": {
                "name": "user_proxy",
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 25,
                "code_execution_config": "local",
                "default_auto_reply": "TERMINATE",
                "description": "User Proxy Agent Configuration",
                "llm_config": False,
                "type": "userproxy",
            }
        }
        sequential_history = []
        for i, agent in enumerate(self.workflow.get("agents", [])):
            workflow = Workflow(
                name="agent workflow", type=WorkFlowType.autonomous, summary_method=WorkFlowSummaryMethod.llm
            )
            workflow = workflow.model_dump(mode="json")
            agent = agent.get("agent")
            workflow["agents"] = [
                {"agent": user_proxy, "link": {"agent_type": "sender"}},
                {"agent": agent, "link": {"agent_type": "receiver"}},
            ]

            auto_workflow = AutoWorkflowManager(
                workflow=workflow,
                history=history,
                work_dir=self.work_dir,
                clear_work_dir=True,
                send_message_function=self.send_message_function,
                a_send_message_function=self.a_send_message_function,
                a_human_input_timeout=self.a_human_input_timeout,
                connection_id=self.connection_id,
            )
            task_prompt = (
                f"""
            Your primary instructions are as follows:
            {agent.get("task_instruction")}
            Context for addressing your task is below:
            =======
            {str(sequential_history)}
            =======
            Now address your task:
            """
                if i > 0
                else message
            )
            result = auto_workflow.run(message=task_prompt, clear_history=clear_history)
            sequential_history.append(result.content)
            self.model_client = auto_workflow.receiver.client
            print(f"======== end of sequence === {i}============")
            self.agent_history.extend(result.meta.get("messages", []))

    async def _a_run_workflow(
        self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False
    ) -> None:
        """
        Asynchronously runs the workflow based on the provided configuration.

        Args:
            message: The initial message to start the chat.
            history: A list of messages to populate the agents' history.
            clear_history: If set to True, clears the chat history before initiating.

        """
        user_proxy = {
            "config": {
                "name": "user_proxy",
                "human_input_mode": "NEVER",
                "max_consecutive_auto_reply": 25,
                "code_execution_config": "local",
                "default_auto_reply": "TERMINATE",
                "description": "User Proxy Agent Configuration",
                "llm_config": False,
                "type": "userproxy",
            }
        }
        sequential_history = []
        for i, agent in enumerate(self.workflow.get("agents", [])):
            workflow = Workflow(
                name="agent workflow", type=WorkFlowType.autonomous, summary_method=WorkFlowSummaryMethod.llm
            )
            workflow = workflow.model_dump(mode="json")
            agent = agent.get("agent")
            workflow["agents"] = [
                {"agent": user_proxy, "link": {"agent_type": "sender"}},
                {"agent": agent, "link": {"agent_type": "receiver"}},
            ]

            auto_workflow = AutoWorkflowManager(
                workflow=workflow,
                history=history,
                work_dir=self.work_dir,
                clear_work_dir=True,
                send_message_function=self.send_message_function,
                a_send_message_function=self.a_send_message_function,
                a_human_input_function=self.a_human_input_function,
                a_human_input_timeout=self.a_human_input_timeout,
                connection_id=self.connection_id,
            )
            task_prompt = (
                f"""
            Your primary instructions are as follows:
            {agent.get("task_instruction")}
            Context for addressing your task is below:
            =======
            {str(sequential_history)}
            =======
            Now address your task:
            """
                if i > 0
                else message
            )
            result = await auto_workflow.a_run(message=task_prompt, clear_history=clear_history)
            sequential_history.append(result.content)
            self.model_client = auto_workflow.receiver.client
            print(f"======== end of sequence === {i}============")
            self.agent_history.extend(result.meta.get("messages", []))

    def _generate_output(
        self,
        message_text: str,
        summary_method: str,
    ) -> str:
        """
        Generates the output response based on the workflow configuration and agent history.

        :param message_text: The text of the incoming message.
        :param flow: An instance of `WorkflowManager`.
        :param flow_config: An instance of `AgentWorkFlowConfig`.
        :return: The output response as a string.
        """

        output = ""
        if summary_method == WorkFlowSummaryMethod.last:
            (self.agent_history)
            last_message = self.agent_history[-1]["message"]["content"] if self.agent_history else ""
            output = last_message
        elif summary_method == WorkFlowSummaryMethod.llm:
            if self.connection_id:
                status_message = SocketMessage(
                    type="agent_status",
                    data={
                        "status": "summarizing",
                        "message": "Summarizing agent dialogue",
                    },
                    connection_id=self.connection_id,
                )
                self.send_message_function(status_message.model_dump(mode="json"))
            output = summarize_chat_history(
                task=message_text,
                messages=self.agent_history,
                client=self.model_client,
            )

        elif summary_method == "none":
            output = ""
        return output

    def run(self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False) -> Message:
        """
        Initiates a chat between the sender and receiver agents with an initial message
        and an option to clear the history.

        Args:
            message: The initial message to start the chat.
            clear_history: If set to True, clears the chat history before initiating.
        """

        start_time = time.time()
        self._run_workflow(message=message, history=history, clear_history=clear_history)
        end_time = time.time()
        output = self._generate_output(message, self.workflow.get("summary_method", "last"))

        result_message = Message(
            content=output,
            role="assistant",
            meta={
                "messages": self.agent_history,
                "summary_method": self.workflow.get("summary_method", "last"),
                "time": end_time - start_time,
                "files": get_modified_files(start_time, end_time, source_dir=self.work_dir),
                "task": message,
            },
        )
        return result_message

    async def a_run(
        self, message: str, history: Optional[List[Message]] = None, clear_history: bool = False
    ) -> Message:
        """
        Asynchronously initiates a chat between the sender and receiver agents with an initial message
        and an option to clear the history.

        Args:
            message: The initial message to start the chat.
            clear_history: If set to True, clears the chat history before initiating.
        """

        start_time = time.time()
        await self._a_run_workflow(message=message, history=history, clear_history=clear_history)
        end_time = time.time()
        output = self._generate_output(message, self.workflow.get("summary_method", "last"))

        result_message = Message(
            content=output,
            role="assistant",
            meta={
                "messages": self.agent_history,
                "summary_method": self.workflow.get("summary_method", "last"),
                "time": end_time - start_time,
                "files": get_modified_files(start_time, end_time, source_dir=self.work_dir),
                "task": message,
            },
        )
        return result_message


class WorkflowManager:
    """
    WorkflowManager class to load agents from a provided configuration and run a chat between them.
    """

    def __new__(
        self,
        workflow: Union[Dict, str],
        history: Optional[List[Message]] = None,
        work_dir: str = None,
        clear_work_dir: bool = True,
        send_message_function: Optional[callable] = None,
        a_send_message_function: Optional[Coroutine] = None,
        a_human_input_function: Optional[callable] = None,
        a_human_input_timeout: Optional[int] = 60,
        connection_id: Optional[str] = None,
    ) -> None:
        """
        Initializes the WorkflowManager with agents specified in the config and optional message history.

        Args:
            workflow (Union[Dict, str]): The workflow configuration. This can be a dictionary or a string which is a path to a JSON file.
            history (Optional[List[Message]]): The message history.
            work_dir (str): The working directory.
            clear_work_dir (bool): If set to True, clears the working directory.
            send_message_function (Optional[callable]): The function to send messages.
            a_send_message_function (Optional[Coroutine]): Async coroutine to send messages.
            a_human_input_function (Optional[callable]): Async coroutine to prompt for user input.
            a_human_input_timeout (Optional[int]): A time (in seconds) to wait for user input.  After this time, the a_human_input_function will timeout and end the conversation.
            connection_id (Optional[str]): The connection identifier.
        """
        if isinstance(workflow, str):
            if os.path.isfile(workflow):
                with open(workflow, "r") as file:
                    self.workflow = json.load(file)
            else:
                raise FileNotFoundError(f"The file {workflow} does not exist.")
        elif isinstance(workflow, dict):
            self.workflow = workflow
        else:
            raise ValueError("The 'workflow' parameter should be either a dictionary or a valid JSON file path")

        if self.workflow.get("type") == WorkFlowType.autonomous.value:
            return AutoWorkflowManager(
                workflow=workflow,
                history=history,
                work_dir=work_dir,
                clear_work_dir=clear_work_dir,
                send_message_function=send_message_function,
                a_send_message_function=a_send_message_function,
                a_human_input_function=a_human_input_function,
                a_human_input_timeout=a_human_input_timeout,
                connection_id=connection_id,
            )
        elif self.workflow.get("type") == WorkFlowType.sequential.value:
            return SequentialWorkflowManager(
                workflow=workflow,
                history=history,
                work_dir=work_dir,
                clear_work_dir=clear_work_dir,
                send_message_function=send_message_function,
                a_send_message_function=a_send_message_function,
                a_human_input_function=a_human_input_function,
                a_human_input_timeout=a_human_input_timeout,
                connection_id=connection_id,
            )


class ExtendedConversableAgent(autogen.ConversableAgent):
    def __init__(
        self,
        message_processor=None,
        a_message_processor=None,
        a_human_input_function=None,
        a_human_input_timeout: Optional[int] = 60,
        connection_id=None,
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)
        self.message_processor = message_processor
        self.a_message_processor = a_message_processor
        self.a_human_input_function = a_human_input_function
        self.a_human_input_response = None
        self.a_human_input_timeout = a_human_input_timeout
        self.connection_id = connection_id

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

    async def a_receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ) -> None:
        if self.a_message_processor:
            await self.a_message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        elif self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        await super().a_receive(message, sender, request_reply, silent)

    # Strangely, when the response from a_get_human_input == "" (empty string) the libs call into the
    # sync version.  I guess that's "just in case", but it's odd because replying with an empty string
    # is the intended way for the user to signal the underlying libs that they want to system to go forward
    # with whatever function call, tool call or AI generated response the request calls for.  Oh well,
    # Que Sera Sera.
    def get_human_input(self, prompt: str) -> str:
        if self.a_human_input_response is None:
            return super().get_human_input(prompt)
        else:
            response = self.a_human_input_response
            self.a_human_input_response = None
            return response

    async def a_get_human_input(self, prompt: str) -> str:
        if self.message_processor and self.a_human_input_function:
            message_dict = {"content": prompt, "role": "system", "type": "user-input-request"}

            message_payload = {
                "recipient": self.name,
                "sender": "system",
                "message": message_dict,
                "timestamp": datetime.now().isoformat(),
                "sender_type": "system",
                "connection_id": self.connection_id,
                "message_type": "agent_message",
            }

            socket_msg = SocketMessage(
                type="user_input_request",
                data=message_payload,
                connection_id=self.connection_id,
            )
            self.a_human_input_response = await self.a_human_input_function(
                socket_msg.dict(), self.a_human_input_timeout
            )
            return self.a_human_input_response

        else:
            result = await super().a_get_human_input(prompt)
            return result


class ExtendedGroupChatManager(autogen.GroupChatManager):
    def __init__(
        self,
        message_processor=None,
        a_message_processor=None,
        a_human_input_function=None,
        a_human_input_timeout: Optional[int] = 60,
        connection_id=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.message_processor = message_processor
        self.a_message_processor = a_message_processor
        self.a_human_input_function = a_human_input_function
        self.a_human_input_response = None
        self.a_human_input_timeout = a_human_input_timeout
        self.connection_id = connection_id

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

    async def a_receive(
        self,
        message: Union[Dict, str],
        sender: autogen.Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ) -> None:
        if self.a_message_processor:
            await self.a_message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        elif self.message_processor:
            self.message_processor(sender, self, message, request_reply, silent, sender_type="agent")
        await super().a_receive(message, sender, request_reply, silent)

    def get_human_input(self, prompt: str) -> str:
        if self.a_human_input_response is None:
            return super().get_human_input(prompt)
        else:
            response = self.a_human_input_response
            self.a_human_input_response = None
            return response

    async def a_get_human_input(self, prompt: str) -> str:
        if self.message_processor and self.a_human_input_function:
            message_dict = {"content": prompt, "role": "system", "type": "user-input-request"}

            message_payload = {
                "recipient": self.name,
                "sender": "system",
                "message": message_dict,
                "timestamp": datetime.now().isoformat(),
                "sender_type": "system",
                "connection_id": self.connection_id,
                "message_type": "agent_message",
            }
            socket_msg = SocketMessage(
                type="user_input_request",
                data=message_payload,
                connection_id=self.connection_id,
            )
            result = await self.a_human_input_function(socket_msg.dict(), self.a_human_input_timeout)
            return result

        else:
            result = await super().a_get_human_input(prompt)
            return result
