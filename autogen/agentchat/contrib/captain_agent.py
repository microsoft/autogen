from typing import Callable, Dict, Literal, Optional, Union

from autogen.agentchat.conversable_agent import ConversableAgent


class CaptainAgent(ConversableAgent):
    """
    (In preview) Captain agent, designed to solve a task with an agent or a group of agents.
    """

    META_PROMPTING_TOOL = {
        "type": "function",
        "function": {
            "name": "meta_prompting",
            "description": "Solve a task by querying an expert. Provide the expert identity and the task that needs to be solved, and the function will return the response of the expert.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "[REQUIRED] The task that needs to be solved by the expert.",
                    },
                    "expert_name": {
                        "type": "string",
                        "description": "[REQUIRED] Name of the expert. Should follow the format: Expert xxx.",
                    },
                    "expert_identity": {
                        "type": "string",
                        "description": "[REQUIRED] A high-quality description about the most capable and suitable expert to answer the instruction. In second person perspective. For example, You are a linguist, well-versed in the study of language and its structures. You are equipped with a good understanding of grammar rules and can differentiate between nouns, verbs, adjectives, adverbs, etc. You can quickly and accurately identify the parts of speech in a sentence and explain the role of each word in the sentence. Your expertise in language and grammar is highly valuable in analyzing and understanding the nuances of communication.",
                    },
                },
            },
        },
    }

    AUTOBUILD_TOOL = {
        "type": "function",
        "function": {
            "name": "seek_experts_help",
            "description": """Build a group of experts and let them chat with each other in a group chat.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_name": {"type": "string", "description": "[REQUIRED] Name of the group."},
                    "building_task": {
                        "type": "string",
                        "description": """Instructions that help a build manager to build a group of experts.""",
                    },
                    "execution_task": {
                        "type": "string",
                        "description": """[REQUIRED] The task that needs the experts to solve by conversation.""",
                    },
                },
            },
        },
    }

    AUTOBUILD_SYSTEM_MESSAGE = """# Your role
You are a perfect manager of a group of advanced experts.

# How to solve the task
When a task is assigned to you:
1. Analysis of its constraints and conditions for completion.
2. Response with a specific plan of how to solve the task.

After that, you can solve the task in two ways:
- Delegate the resolution of tasks to other experts created by seeking a group of experts for help and derive conclusive insights from their conversation summarization.
- Analysis and solve the task with your coding and language skills.

# How to seek experts help
The tool "seek_experts_help" can build a group of experts according to the building_task and let them chat with each other in a group chat to solve the execution_task you provided.
- This tool will summarize the essence of the experts' conversation and the derived conclusions.
- You should not modify any task information from meta_user_proxy, including code blocks, but you can provide extra information.
- Within a single response, you are limited to initiating one group of experts.

## building_task
This task helps a build manager to build a group of experts for your task.
You should suggest less then three roles (including a checker for verification) with the following format.

### Format
- [Detailed description for role 1]
- [Detailed description for role 2]
- [Detailed description for checker]

## execution_task
This is the task that needs the experts to solve by conversation.
You should Provide the following information in markdown format.

### Format
## Task description
...
## Plan for solving the task
...
## Output format
...
## Constraints and conditions for completion
...
## [Optional] results (including code blocks) and reason from last response
...

# After seek_experts_help
You will receive a comprehensive conclusion from the conversation, including the task information, results, reason for the results, conversation contradiction or issues, and additional information.
You **must** conduct a thorough verification for the result and reason's logical compliance by leveraging the step-by-step backward reasoning with the same group of experts (with the same group name) when:
- The conversation has contradictions or issues (need double-check marked as yes), or
- The result is different from the previous results.

Note that the previous experts will forget everything after you obtain the response from them. You should provide the results (including code blocks) you collected from the previous experts' response and put it in the new execution_task.

# Some useful instructions
- You only have one tool called "seek_experts_help".
- Provide a answer yourself after "seek_experts_help".
- You should suggest python code in a python coding block (```python...```).
- When using code, you must indicate the script type in the code block.
- Do not suggest incomplete code which requires users to modify.
- Be clear about which step uses code, which step uses your language skill, and which step to build a group chat.
- If the code's result indicates there is an error, fix the error and output the code again.
- If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
- When you find an answer, verify the answer carefully.
- Include verifiable evidence in your response if possible.
- After completing all tasks and verifications, you should conclude the operation and reply "TERMINATE"
"""

    META_PROMPTING_SYSTEM_MESSAGE = """You are Meta-Expert, an extremely clever expert with the unique ability to collaborate with multiple experts (such as Expert Problem Solver, Expert Mathematician, Expert Essayist, etc.) to tackle any task and solve any complex problems. Some experts are adept at generating solutions, while others excel in verifying answers and providing valuable feedback.

As Meta-Expert, your role is to oversee the communication between the experts, effectively using their skills to answer a given question while applying your own critical thinking and verification abilities.

To communicate with a expert, call function "meta_prompting" with the expert's name, identity information and the task that needs to be solved. The function will return a response from the expert.

Ensure that your instructions are clear and unambiguous, and include all necessary information within the triple quotes. You should assign personas to the experts (e.g., "You are a physicist specialized in...").

You can interact with only one expert at a time, and break complex problems into smaller, solvable tasks if needed. Each interaction is treated as an isolated event, so include all relevant details in every call.

If you or an expert finds a mistake in another expert's solution, ask a new expert to review the details, compare both solutions, and give feedback. You can request an expert to redo their calculations or work, using input from other experts. Keep in mind that all experts, except yourself, have no memory! Therefore, always provide complete information in your instructions when contacting them. Since experts can sometimes make errors, seek multiple opinions or independently verify the solution if uncertain. Before providing a final answer, always consult an expert for confirmation. Ideally, obtain or verify the final solution with two independent experts. However, aim to present your final answer within 15 rounds or fewer.

Refrain from repeating the very same questions to experts. Examine their responses carefully and seek clarification if required, keeping in mind they don't recall past interactions.

Upon the completion of all tasks and verifications, you should conclude the operation and reply "TERMINATE" in the end.
"""

    DEFAULT_DESCRIPTION = "A helpful AI assistant that can build a group of agents at a proper time to solve a task."

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
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
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            description=description,
            **kwargs,
        )

        if nested_mode == "autobuild":
            if system_message is None:
                system_message = self.AUTOBUILD_SYSTEM_MESSAGE
            self.update_tool_signature(self.AUTOBUILD_TOOL, is_remove=False)
        elif nested_mode == "meta_prompting":
            if system_message is None:
                system_message = self.META_PROMPTING_SYSTEM_MESSAGE
            self.update_tool_signature(self.META_PROMPTING_TOOL, is_remove=False)
        else:
            raise 'Invalid nested_mode, should be "autobuild" or "meta_prompting".'

        self.update_system_message(system_message)
