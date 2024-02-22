from typing import Callable, Dict, Literal, Optional, Union
from autogen.agentchat.conversable_agent import ConversableAgent


class MetaAgent(ConversableAgent):
    """
    (In preview) Meta agent, designed to solve a task with an agent or a group of agents.
    """

    # input: agent's system message
    META_PROMPTING_TOOL = {"type": "function", "function": {"name": "meta_prompting"}}

    AUTOBUILD_QUERY_TOOL = {
        "type": "function",
        "function": {
            "name": "autobuild_by_name",
            "description": "Query a previously built group of experts by name and use them to solve the execution_task you provide.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_name": {"type": "string", "description": "[REQUIRED] Name of the group."},
                    "execution_task": {
                        "type": "string",
                        "description": "[REQUIRED] Task that need the experts to solve by conversation.",
                    },
                },
            },
            "required": ["group_name", "execution_task"],
        },
    }

    # input: task
    AUTOBUILD_TOOL = {
        "type": "function",
        "function": {
            "name": "autobuild",
            "description": "Use building_task to build a group of experts to solve your execution_task. This function will return the summarization of the group chat history provided by the participant experts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_name": {"type": "string", "description": "[REQUIRED] Name of the group."},
                    "building_task": {
                        "type": "string",
                        "description": "[REQUIRED] Instructions that helps the manager to build a group of experts for your task.",
                    },
                    "execution_task": {
                        "type": "string",
                        "description": "[REQUIRED] Task that need the experts to solve by conversation.",
                    },
                },
            },
            "required": ["group_name", "building_task", "execution_task"],
        },
    }

    DEFAULT_SYSTEM_MESSAGE = """As a manager, your primary objective is to delegate the resolution of tasks to other AI agents through structured dialogue and derive conclusive insights from their interaction records.

Upon task assignment, assess the task to discern its complexities and, if necessary, segment it into more manageable subtasks. Subsequently, you have the option to either tackle these subtasks individually or facilitate the resolution process through the creation of a singular agent via "meta_prompting" or a group of agents using "autobuild".

It is important to note that within a single response, you are limited to initiating either one solitary agent or a collective of agents.

The "meta_prompting" and "autobuild" functions will yield a summary with the dialogue's essence and the derived conclusions. Upon receipt of these outcomes, it is crucial to conduct a thorough verification using programming or alternative AI agents to ensure accuracy and reliability.

Upon the completion of all tasks and verifications, you should conclude the operation by responding with "TERMINATE".
"""

    DEFAULT_DESCRIPTION = "A helpful AI assistant that can build a group of agents at a proper time to solve a task."

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, Literal[False]]] = False,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        nested_mode: Optional[str] = "autobuild",
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            llm_config (dict): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                The limit only plays a role when human_input_mode is not "ALWAYS".
            nested_mode (str): the mode meta agent use to create nested chat.
                Should be in "meta_prompting" or "autobuild".
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            description=description,
            **kwargs,
        )

        # self.register_function(function_map={name: lambda **args: execute_func(name, packages, code, **args)})
        if nested_mode == "autobuild":
            self.update_tool_signature(self.AUTOBUILD_TOOL, is_remove=False)
            self.update_tool_signature(self.AUTOBUILD_QUERY_TOOL, is_remove=False)
        elif nested_mode == "meta_prompting":
            self.update_tool_signature(self.META_PROMPTING_TOOL, is_remove=False)
        else:
            raise 'Invalid nested_mode, should be "autobuild" or "meta_prompting".'
