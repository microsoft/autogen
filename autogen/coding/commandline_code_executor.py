import uuid
import warnings
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field

from ..agentchat.agent import LLMAgent
from ..code_utils import DEFAULT_TIMEOUT, WORKING_DIR, execute_code
from .base import CodeBlock, CodeExtractor, CodeResult
from .markdown_code_extractor import MarkdownCodeExtractor

try:
    from termcolor import colored
except ImportError:

    def colored(x: Any, *args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
        return x  # type: ignore[no-any-return]


__all__ = ("CommandlineCodeExecutor",)


class CommandlineCodeExecutor(BaseModel):
    """A code executor class that executes code through a terminal command line
    environment.

    By default, this code executor uses a docker container to execute code.
    It can be configured to execute code locally without docker
    but it's not recommended.

    Each code block is saved as a file and executed in a separate process in
    the working directory, and a unique filename is generated for each code
    block. The code blocks are executed in the order they are received.
    Currently the only supported languages is Python and shell scripts.
    For Python code, use the language "python" for the code block.
    For shell scripts, use the language "bash", "shell", or "sh" for the code
    block.

    Args:
        timeout (int): The timeout for code execution.
        work_dir (str): The working directory for the code execution. If None,
            a default working directory will be used. The default working
            directory is the "extensions" directory under path to `autogen`.
        use_docker (bool): Whether to use a docker container for code
            execution. If False, the code will be executed in the current
            environment. Default is True.
        docker_image_name (str): The optional docker image to use for code
            execution. `use_docker` must be True for this to take effect.
            If not provided, a default image will be created based on
            python:3-slim and used for code execution.
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

        def add_to_agent(self, agent: LLMAgent) -> None:
            """Add this capability to an agent."""
            system_message = agent.system_message + self.DEFAULT_SYSTEM_MESSAGE_UPDATE
            agent.update_system_message(system_message)

    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, ge=1)
    work_dir: Optional[str] = Field(default=WORKING_DIR)
    use_docker: bool = Field(default=True)
    docker_image_name: Optional[str] = None

    def _get_use_docker_for_code_utils(self) -> Optional[Union[List[str], str, bool]]:
        if self.use_docker is False:
            return False
        if self.docker_image_name is not None:
            # Docker image name is set, use it.
            return self.docker_image_name
        # Docker image name has not being set, use the default.
        return self.use_docker

    @property
    def user_capability(self) -> "CommandlineCodeExecutor.UserCapability":
        """Export a user capability that can be added to an agent."""
        return CommandlineCodeExecutor.UserCapability()

    @property
    def code_extractor(self) -> CodeExtractor:
        """Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CodeResult:
        """Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CodeResult: The result of the code execution."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            lang, code = code_block.language, code_block.code
            print(
                colored(
                    f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                    "red",
                ),
                flush=True,
            )
            filename_uuid = uuid.uuid4().hex
            if lang in ["bash", "shell", "sh"]:
                filename = f"{filename_uuid}.{lang}"
                exitcode, logs, image = execute_code(
                    code=code,
                    lang=lang,
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    filename=filename,
                    use_docker=self._get_use_docker_for_code_utils(),
                )
            elif lang in ["python", "Python"]:
                filename = f"{filename_uuid}.py"
                exitcode, logs, image = execute_code(
                    code=code,
                    lang="python",
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    filename=filename,
                    use_docker=self._get_use_docker_for_code_utils(),
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = (1, f"unknown language {lang}", None)
                # raise NotImplementedError
            if image is not None:
                # Update the image to use for the next execution.
                self.docker_image_name = image
            logs_all += "\n" + logs
            if exitcode != 0:
                break
        return CodeResult(exit_code=exitcode, output=logs_all)

    def restart(self) -> None:
        """Restart the code executor."""
        warnings.warn("Restarting command line code executor is not supported. No action is taken.")
