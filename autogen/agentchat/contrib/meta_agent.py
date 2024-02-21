from typing import Callable, Dict, Literal, Optional, Union
from autogen.agentchat.conversable_agent import ConversableAgent


class MetaAgent(ConversableAgent):
    """
    (In preview) Meta agent, designed to solve a task with an agent or a group of agents.
    """

    # input: agent's system message
    META_PROMPTING_TOOL = {
        "type": "function",
        "function": {
            "name": "meta_prompting"
        }
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
                    "building_task": {
                        "type": "string",
                        "description": "Instructions that helps the manager to build a group of experts for your task."
                    },
                    "execution_task": {
                        "type": "string",
                        "description": "Task that need the experts to solve by conversation."
                    },
                }
            },
            "required": ["task"]
        }
    }

    DEFAULT_SYSTEM_MESSAGE = """You are a helpful AI assistant.
Once you receive a task from user, you should analysis it and divide the task into multiple subtasks. 
Then you can either solve the subtask one by one by yourself, or create an agent by "meta_prompting" or a group of agents by "autobuild" to solve the subtask by following the function's instruction.
Note that you can only create one agent or a group of agents at a time.
"meta_prompting" and "autobuild" will return a summary of the conversation history and result from agents created by "meta_prompting" or "autobuild".
When you receive the result, verify it carefully by code or another group of agents.
When everything is done, please reply "TERMINATE".
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
        elif nested_mode == "meta_prompting":
            self.update_tool_signature(self.META_PROMPTING_TOOL, is_remove=False)
        else:
            raise "Invalid nested_mode, should be \"autobuild\" or \"meta_prompting\"."
