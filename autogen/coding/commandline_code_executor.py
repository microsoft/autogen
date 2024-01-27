from typing import List, Optional, Union

from pydantic import BaseModel, Field

from autogen.coding.base import CodeBlock, CodeExtractor, CodeResult
from autogen.coding.markdown_code_extractor import MarkdownCodeExtractor

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.code_utils import DEFAULT_TIMEOUT, WORKING_DIR, execute_code


class CommandlineCodeExecutor(BaseModel):
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

    timeout: Optional[int] = Field(default=DEFAULT_TIMEOUT, ge=1)
    filename: Optional[str] = None
    work_dir: Optional[str] = Field(default=WORKING_DIR)
    use_docker: Optional[Union[List[str], str, bool]] = None
    docker_image_name: Optional[str] = None

    def _get_use_docker_for_code_utils(self):
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
        """Execute the code blocks and return the result."""
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
            if lang in ["bash", "shell", "sh"]:
                exitcode, logs, image = execute_code(
                    code=code,
                    lang=lang,
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    filename=self.filename,
                    use_docker=self._get_use_docker_for_code_utils(),
                )
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = execute_code(
                    code,
                    lang="python",
                    filename=filename,
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    use_docker=self._get_use_docker_for_code_utils(),
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, image = (
                    1,
                    f"unknown language {lang}",
                    None,
                )
                # raise NotImplementedError
            if image is not None:
                # Update the image to use for the next execution.
                self.docker_image_name = image
            logs_all += "\n" + logs
            if exitcode != 0:
                break
        return CodeResult(exit_code=exitcode, output=logs_all)

    def reset(self) -> None:
        """Reset the code executor."""
        # Reset the image to None so that the next execution will use a new image.
        self.docker_image_name = None
