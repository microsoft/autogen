import json
import autogen
from .agent_builder import AgentBuilder
from typing import Callable, Dict, List, Literal, Optional, Union
from autogen.agentchat.conversable_agent import ConversableAgent


def check_nested_mode_config(nested_mode_config: Dict):
    if "autobuild_init_config" in nested_mode_config.keys():
        assert (
            "autobuild_build_config" in nested_mode_config.keys()
        ), "autobuild_build_config is required when using autobuild as nested mode."
        assert (
            "group_chat_llm_config" in nested_mode_config.keys()
        ), "group_chat_llm_config is required when using autobuild as nested mode."
    elif "meta_prompting_llm_config" in nested_mode_config.keys():
        # TODO: check meta_prompting_config
        pass
    else:
        raise ValueError("nested_mode_config should contain either autobuild_init_config or meta_prompting_llm_config.")


class MetaUserProxyAgent(ConversableAgent):
    """(In preview) A proxy agent for the meta agent, that can execute code and provide feedback to the other agents."""

    SUMMARY_PROMPT = """
Briefly summarize the conversation history derive from a group chat.
You should highlight the reasoning process and the conclusion they made.

Conversation history:
{chat_history}
"""

    DEFAULT_AUTO_REPLY = (
        "Thank you. Please keep solving the problem. If you think the problem is solved, please reply me only with 'TERMINATE'."
    )

    # Default UserProxyAgent.description values, based on human_input_mode
    DEFAULT_USER_PROXY_AGENT_DESCRIPTIONS = {
        "ALWAYS": "An attentive HUMAN user who can answer questions about the task, and can perform tasks such as running Python code or inputting command line commands at a Linux terminal and reporting back the execution results.",
        "TERMINATE": "A user that can run Python code or input command line commands at a Linux terminal and report back the execution results.",
        "NEVER": "A computer terminal that can running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks), or the conversation history and result of a group of agents",
    }

    def __init__(
        self,
        name: str,
        nested_mode_config: Dict,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = DEFAULT_AUTO_REPLY,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        system_message: Optional[Union[str, List]] = "",
        description: Optional[str] = None,
    ):
        """
        Args:
            name (str): name of the agent.
            nested_mode_config (dict): the configuration for the nested chat mode.
                For autobuild, please refer to: autogen.agentchat.contrib.agent_builder[AgentBuilder]
                TODO: Add meta_prompting description
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
            function_map (dict[str, callable]): Mapping function names (passed to openai) to callable functions.
            code_execution_config (dict or False): config for the code execution.
                To disable code execution, set to False. Otherwise, set to a dictionary with the following keys:
                - work_dir (Optional, str): The working directory for the code execution.
                    If None, a default working directory will be used.
                    The default working directory is the "extensions" directory under
                    "path_to_autogen".
                - use_docker (Optional, list, str or bool): The docker image to use for code execution.
                    Default is True, which means the code will be executed in a docker container. A default list of images will be used.
                    If a list or a str of image name(s) is provided, the code will be executed in a docker container
                    with the first image successfully pulled.
                    If False, the code will be executed in the current environment.
                    We strongly recommend using docker for code execution.
                - timeout (Optional, int): The maximum execution time in seconds.
                - last_n_messages (Experimental, Optional, int): The number of messages to look back for code execution. Default to 1.
            default_auto_reply (str or dict or None): the default auto reply message when no code execution or llm based reply is generated.
            llm_config (dict or False): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
                Default to false, which disables llm-based auto reply.
            system_message (str or List): system message for ChatCompletion inference.
                Only used when llm_config is not False. Use it to reprogram the agent.
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)
        """
        description = (
            description if description is not None else self.DEFAULT_USER_PROXY_AGENT_DESCRIPTIONS[human_input_mode]
        )
        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
            description=description,
        )
        self.register_function(
            function_map={
                "autobuild": lambda **args: self._run_autobuild(**args),
                "autobuild_by_name": lambda **args: self._run_autobuild(**args),
                "meta_prompting": lambda **args: self._run_meta_prompting(**args),
            }
        )
        check_nested_mode_config(nested_mode_config)
        self._nested_mode_config = nested_mode_config.copy()
        self._code_execution_config = code_execution_config.copy()
        self.build_history = {}

    def _run_autobuild(self, group_name: str, execution_task: str, building_task: str = "") -> str:
        """
        Build a group of agents by AutoBuild to solve the task.
        This function requires the nested_mode_config to contain the autobuild_init_config,
            autobuild_llm_config, group_chat_llm_config.
        """
        print("==> Running AutoBuild...", flush=True)
        print("==> Building task: ", building_task, flush=True)
        print("==> Execution task: ", execution_task, flush=True)

        builder = AgentBuilder(**self._nested_mode_config["autobuild_init_config"])
        if group_name in self.build_history.keys():
            agent_list, agent_configs = builder.load(config_json=json.dumps(self.build_history[group_name]))
        else:
            agent_list, agent_configs = builder.build(
                building_task, **self._nested_mode_config["autobuild_build_config"]
            )
            self.build_history[group_name] = agent_configs.copy()

        # start nested chat
        nested_group_chat = autogen.GroupChat(
            agents=agent_list, messages=[], **self._nested_mode_config["group_chat_config"]
        )
        manager = autogen.GroupChatManager(
            groupchat=nested_group_chat, llm_config=self._nested_mode_config["group_chat_llm_config"]
        )
        agent_list[0].initiate_chat(manager, message=execution_task)

        chat_history = []
        key = list(agent_list[0].chat_messages.keys())[0]
        chat_messages = agent_list[0].chat_messages[key]
        for item in chat_messages:
            chat_history.append(item)

        # Summarize the group chat history, we use builder model to summarize the conversation history.
        summary_model_config_list = autogen.config_list_from_json(
            builder.config_file_or_env,
            file_location=builder.config_file_location,
            filter_dict={"model": [builder.builder_model]},
        )
        summary_model = autogen.OpenAIWrapper(config_list=summary_model_config_list)
        summarized_history = (
            summary_model.create(
                messages=[
                    {
                        "role": "user",
                        "content": self.SUMMARY_PROMPT.format(chat_history=chat_history),
                    }
                ]
            )
            .choices[0]
            .message.content
        )
        return summarized_history

    def _run_meta_prompting(self, expert_name: str, expert_identity: str, task: str) -> str:
        """
        Run Meta-prompting to solve the task.
        The method is adapted from "Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding".
        Paper available at https://arxiv.org/abs/2401.12954
        """
        print("Running meta prompting...")
        print("Querying expert: ", expert_name)

        expert = autogen.AssistantAgent(
            name=expert_name,
            human_input_mode="NEVER",
            llm_config=self._nested_mode_config["meta_prompting_llm_config"],
            system_message='You are an AI assistant that helps people find information. Please answer the following question. Once you have determined the final answer, please present it using the format below:\n\n>> FINAL ANSWER:\n"""\n[final answer]\n"""',
            max_consecutive_auto_reply=1,
        )
        user_proxy = autogen.UserProxyAgent(
            name="proxy",
            human_input_mode="NEVER",
            default_auto_reply="TERMINATE",
            code_execution_config=self._code_execution_config,
            max_consecutive_auto_reply=1,
        )
        task += "\nYou have access to python code interpreter. Suggest python code block starting with '```python' and the code will be automatically executed. You can use code to solve the task or for result verification. You should always use print statement to get the value of a variable."
        user_proxy.initiate_chat(expert, message=expert_identity + "\n" + task, silent=True)

        expert_reply = user_proxy.chat_messages[expert][1]["content"]
        proxy_reply = user_proxy.chat_messages[expert][2]["content"]

        if proxy_reply != "TERMINATE":
            # Code is suggested by the expert
            code_result = proxy_reply[proxy_reply.find("Code output:") + len("Code output:"):].strip()
            expert_reply += f"\nThis is the output of the code blocks when executed:\n{code_result}"
        else:
            expert_reply.replace(
                "FINAL ANSWER:",
                f"{expert_name}'s final answer:\n",
            )

        return expert_reply
