from __future__ import annotations
from typing import Dict, Tuple

from autogen.coding.base import CodeBlock, CodeResult

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.code_utils import execute_code


class CommandlineCodeExecutor:
    """A code executor class that executes code through command line without persisting
    any state in memory between executions.

    Each execution is independent of each other. By default, it uses docker to
    execute code. It can be configured to execute code locally without docker
    but it's not recommended.
    """

    class UserCapability:
        """An AgentCapability class that gives agent ability use a command line
        code executor."""

        DEFAULT_SYSTEM_MESSAGE_UPDATE = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

        def add_to_agent(self, agent):
            """Add this capability to an agent."""
            agent.update_system_message(agent.system_message + self.DEFAULT_SYSTEM_MESSAGE_UPDATE)

    def __init__(self, code_execution_config: Dict):
        self._code_execution_config = code_execution_config.copy()

    @property
    def user_capability(self) -> CommandlineCodeExecutor.UserCapability:
        """Export a user capability that can be added to an agent."""
        return CommandlineCodeExecutor.UserCapability()

    @property
    def code_execution_config(self) -> Dict:
        """Return the code execution config."""
        return self._code_execution_config

    def execute_code(self, code_block: CodeBlock, **kwargs) -> CodeResult:
        """Execute code and return the result."""
        args = self._code_execution_config.copy()
        args.update(kwargs)
        # Remove arguments not in execute_code.
        for key in list(args.keys()):
            if key not in execute_code.__code__.co_varnames:
                args.pop(key)
        # Remove lang argument as we are getting it from code_block.
        args.pop("lang", None)
        # Execute code and obtain a docker image name if created.
        exit_code, output, docker_image_name = execute_code(code_block.code, lang=code_block.language, **args)
        if docker_image_name is not None:
            self._code_execution_config["use_docker"] = docker_image_name
        return CodeResult(exit_code=exit_code, output=output, docker_image_name=docker_image_name)

    def reset(self) -> None:
        """Reset the code executor."""
        # Reset the image to None so that the next execution will use a new image.
        self._code_execution_config["use_docker"] = None
