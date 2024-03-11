import os
from pathlib import Path
import re
import uuid
import warnings
from typing import ClassVar, List, Optional, Union
from pydantic import Field

from ..agentchat.agent import LLMAgent
from ..code_utils import execute_code
from .base import CodeBlock, CodeExecutor, CodeExtractor, CodeResult
from .markdown_code_extractor import MarkdownCodeExtractor

__all__ = (
    "LocalCommandLineCodeExecutor",
    "CommandLineCodeResult",
)


class CommandLineCodeResult(CodeResult):
    """(Experimental) A code result class for command line code executor."""

    code_file: Optional[str] = Field(
        default=None,
        description="The file that the executed code block was saved to.",
    )


class LocalCommandLineCodeExecutor(CodeExecutor):
    DEFAULT_SYSTEM_MESSAGE_UPDATE: ClassVar[
        str
    ] = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

    def __init__(
        self,
        timeout: int = 60,
        work_dir: Union[Path, str] = Path("."),
        system_message_update: str = DEFAULT_SYSTEM_MESSAGE_UPDATE,
    ):
        """(Experimental) A code executor class that executes code through a local command line
        environment.

        **This will execute LLM generated code on the local machine.**

        Each code block is saved as a file and executed in a separate process in
        the working directory, and a unique file is generated and saved in the
        working directory for each code block.
        The code blocks are executed in the order they are received.
        Command line code is sanitized using regular expression match against a list of dangerous commands in order to prevent self-destructive
        commands from being executed which may potentially affect the users environment.
        Currently the only supported languages is Python and shell scripts.
        For Python code, use the language "python" for the code block.
        For shell scripts, use the language "bash", "shell", or "sh" for the code
        block.

        Args:
            timeout (int): The timeout for code execution. Default is 60.
            work_dir (str): The working directory for the code execution. If None,
                a default working directory will be used. The default working
                directory is the current directory ".".
            system_message_update (str): The system message update for agent that
            produces code to run on this executor.
            Default is `LocalCommandLineCodeExecutor.DEFAULT_SYSTEM_MESSAGE_UPDATE`.

        """

        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)

        if not work_dir.exists():
            raise ValueError(f"Working directory {work_dir} does not exist.")

        self._timeout = timeout
        self._work_dir: Path = work_dir
        self._system_message_update = system_message_update

    class UserCapability:
        """An AgentCapability class that gives agent ability use a command line
        code executor via a system message update. This capability can be added
        to an agent using the `add_to_agent` method."""

        def __init__(self, system_message_update: str) -> None:
            self.system_message_update = system_message_update

        def add_to_agent(self, agent: LLMAgent) -> None:
            """Add this capability to an agent by updating the agent's system
            message."""
            agent.update_system_message(agent.system_message + self.system_message_update)

    @property
    def user_capability(self) -> "LocalCommandLineCodeExecutor.UserCapability":
        """Export a user capability for this executor that can be added to
        an agent that produces code to be executed by this executor."""
        return LocalCommandLineCodeExecutor.UserCapability(self._system_message_update)

    @property
    def timeout(self) -> int:
        """(Experimental) The timeout for code execution."""
        return self._timeout

    @property
    def work_dir(self) -> Path:
        """(Experimental) The working directory for the code execution."""
        return self._work_dir

    @property
    def code_extractor(self) -> CodeExtractor:
        """(Experimental) Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    @staticmethod
    def sanitize_command(lang: str, code: str) -> None:
        """
        Sanitize the code block to prevent dangerous commands.
        This approach acknowledges that while Docker or similar
        containerization/sandboxing technologies provide a robust layer of security,
        not all users may have Docker installed or may choose not to use it.
        Therefore, having a baseline level of protection helps mitigate risks for users who,
        either out of choice or necessity, run code outside of a sandboxed environment.
        """
        dangerous_patterns = [
            (r"\brm\s+-rf\b", "Use of 'rm -rf' command is not allowed."),
            (r"\bmv\b.*?\s+/dev/null", "Moving files to /dev/null is not allowed."),
            (r"\bdd\b", "Use of 'dd' command is not allowed."),
            (r">\s*/dev/sd[a-z][1-9]?", "Overwriting disk blocks directly is not allowed."),
            (r":\(\)\{\s*:\|\:&\s*\};:", "Fork bombs are not allowed."),
        ]
        if lang in ["bash", "shell", "sh"]:
            for pattern, message in dangerous_patterns:
                if re.search(pattern, code):
                    raise ValueError(f"Potentially dangerous command detected: {message}")

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CommandLineCodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CommandLineCodeResult: The result of the code execution."""
        logs_all = ""
        for code_block in code_blocks:
            lang, code = code_block.language, code_block.code

            LocalCommandLineCodeExecutor.sanitize_command(lang, code)
            filename_uuid = uuid.uuid4().hex
            filename = None
            if lang in ["bash", "shell", "sh", "pwsh", "powershell", "ps1"]:
                filename = f"{filename_uuid}.{lang}"
                exitcode, logs, _ = execute_code(
                    code=code,
                    lang=lang,
                    timeout=self._timeout,
                    work_dir=str(self._work_dir),
                    filename=filename,
                    use_docker=False,
                )
            elif lang in ["python", "Python"]:
                filename = f"{filename_uuid}.py"
                exitcode, logs, _ = execute_code(
                    code=code,
                    lang="python",
                    timeout=self._timeout,
                    work_dir=str(self._work_dir),
                    filename=filename,
                    use_docker=False,
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, _ = (1, f"unknown language {lang}", None)
            logs_all += "\n" + logs
            if exitcode != 0:
                break

        code_filename = str(self._work_dir / filename) if filename is not None else None
        return CommandLineCodeResult(exit_code=exitcode, output=logs_all, code_file=code_filename)

    def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        warnings.warn("Restarting local command line code executor is not supported. No action is taken.")


# From stack overflow: https://stackoverflow.com/a/52087847/2214524
class _DeprecatedClassMeta(type):
    def __new__(cls, name, bases, classdict, *args, **kwargs):
        alias = classdict.get("_DeprecatedClassMeta__alias")

        if alias is not None:

            def new(cls, *args, **kwargs):
                alias = getattr(cls, "_DeprecatedClassMeta__alias")

                if alias is not None:
                    warnings.warn(
                        "{} has been renamed to {}, the alias will be "
                        "removed in the future".format(cls.__name__, alias.__name__),
                        DeprecationWarning,
                        stacklevel=2,
                    )

                return alias(*args, **kwargs)

            classdict["__new__"] = new
            classdict["_DeprecatedClassMeta__alias"] = alias

        fixed_bases = []

        for b in bases:
            alias = getattr(b, "_DeprecatedClassMeta__alias", None)

            if alias is not None:
                warnings.warn(
                    "{} has been renamed to {}, the alias will be "
                    "removed in the future".format(b.__name__, alias.__name__),
                    DeprecationWarning,
                    stacklevel=2,
                )

            # Avoid duplicate base classes.
            b = alias or b
            if b not in fixed_bases:
                fixed_bases.append(b)

        fixed_bases = tuple(fixed_bases)

        return super().__new__(cls, name, fixed_bases, classdict, *args, **kwargs)

    def __instancecheck__(cls, instance):
        return any(cls.__subclasscheck__(c) for c in {type(instance), instance.__class__})

    def __subclasscheck__(cls, subclass):
        if subclass is cls:
            return True
        else:
            return issubclass(subclass, getattr(cls, "_DeprecatedClassMeta__alias"))


class LocalCommandlineCodeExecutor(metaclass=_DeprecatedClassMeta):
    """LocalCommandlineCodeExecutor renamed to LocalCommandLineCodeExecutor"""

    _DeprecatedClassMeta__alias = LocalCommandLineCodeExecutor


class CommandlineCodeResult(metaclass=_DeprecatedClassMeta):
    """CommandlineCodeResult renamed to CommandLineCodeResult"""

    _DeprecatedClassMeta__alias = CommandLineCodeResult
