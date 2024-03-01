import os
import re
import uuid
import warnings
from typing import Any, ClassVar, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..agentchat.agent import LLMAgent
from ..code_utils import execute_code
from .base import CodeBlock, CodeExtractor, CodeResult
from .markdown_code_extractor import MarkdownCodeExtractor

try:
    from termcolor import colored
except ImportError:

    def colored(x: Any, *args: Any, **kwargs: Any) -> str:  # type: ignore[misc]
        return x  # type: ignore[no-any-return]


__all__ = (
    "LocalCommandlineCodeExecutor",
    "CommandlineCodeResult",
)


class CommandlineCodeResult(CodeResult):
    """(Experimental) A code result class for command line code executor."""

    code_file: Optional[str] = Field(
        default=None,
        description="The file that the executed code block was saved to.",
    )


class LocalCommandlineCodeExecutor(BaseModel):
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
    """

    timeout: int = Field(default=60, ge=1, description="The timeout for code execution.")
    work_dir: str = Field(default=".", description="The working directory for the code execution.")

    @field_validator("work_dir")
    @classmethod
    def _check_work_dir(cls, v: str) -> str:
        if os.path.exists(v):
            return v
        raise ValueError(f"Working directory {v} does not exist.")

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

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CommandlineCodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CommandlineCodeResult: The result of the code execution."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            lang, code = code_block.language, code_block.code

            LocalCommandlineCodeExecutor.sanitize_command(lang, code)

            print(
                colored(
                    f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                    "red",
                ),
                flush=True,
            )
            filename_uuid = uuid.uuid4().hex
            filename = None
            if lang in ["bash", "shell", "sh", "pwsh", "powershell", "ps1"]:
                filename = f"{filename_uuid}.{lang}"
                exitcode, logs, _ = execute_code(
                    code=code,
                    lang=lang,
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    filename=filename,
                    use_docker=False,
                )
            elif lang in ["python", "Python"]:
                filename = f"{filename_uuid}.py"
                exitcode, logs, _ = execute_code(
                    code=code,
                    lang="python",
                    timeout=self.timeout,
                    work_dir=self.work_dir,
                    filename=filename,
                    use_docker=False,
                )
            else:
                # In case the language is not supported, we return an error message.
                exitcode, logs, _ = (1, f"unknown language {lang}", None)
            logs_all += "\n" + logs
            if exitcode != 0:
                break
        code_filename = os.path.join(self.work_dir, filename) if filename is not None else None
        return CommandlineCodeResult(exit_code=exitcode, output=logs_all, code_file=code_filename)

    def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        warnings.warn("Restarting local command line code executor is not supported. No action is taken.")
