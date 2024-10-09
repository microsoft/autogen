# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/local_commandline_code_executor.py
# Credit to original authors

import asyncio
import logging
import sys
import warnings
from hashlib import md5
from pathlib import Path
from string import Template
from typing import Any, Callable, ClassVar, List, Sequence, Union

from typing_extensions import ParamSpec

from ....base import CancellationToken
from .._base import CodeBlock, CodeExecutor
from .._func_with_reqs import (
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
    build_python_functions_file,
    to_stub,
)
from .command_line_code_result import CommandLineCodeResult
from .utils import PYTHON_VARIANTS, get_file_name_from_content, lang_to_cmd, silence_pip  # type: ignore

__all__ = ("LocalCommandLineCodeExecutor",)

A = ParamSpec("A")


class LocalCommandLineCodeExecutor(CodeExecutor):
    SUPPORTED_LANGUAGES: ClassVar[List[str]] = [
        "bash",
        "shell",
        "sh",
        "pwsh",
        "powershell",
        "ps1",
        "python",
    ]
    FUNCTION_PROMPT_TEMPLATE: ClassVar[
        str
    ] = """You have access to the following user defined functions. They can be accessed from the module called `$module_name` by their function names.

For example, if there was a function called `foo` you could import it by writing `from $module_name import foo`

$functions"""

    def __init__(
        self,
        timeout: int = 60,
        work_dir: Union[Path, str] = Path("."),
        functions: Sequence[
            Union[
                FunctionWithRequirements[Any, A],
                Callable[..., Any],
                FunctionWithRequirementsStr,
            ]
        ] = [],
        functions_module: str = "functions",
    ):
        """A code executor class that executes code through a local command line
        environment.

        .. danger::

            This will execute code on the local machine. If being used with LLM generated code, caution should be used.

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
            timeout (int): The timeout for the execution of any single code block. Default is 60.
            work_dir (str): The working directory for the code execution. If None,
                a default working directory will be used. The default working
                directory is the current directory ".".
            functions (List[Union[FunctionWithRequirements[Any, A], Callable[..., Any]]]): A list of functions that are available to the code executor. Default is an empty list.
            functions_module (str, optional): The name of the module that will be created to store the functions. Defaults to "functions".

        """

        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)

        if not functions_module.isidentifier():
            raise ValueError("Module name must be a valid Python identifier")

        self._functions_module = functions_module

        work_dir.mkdir(exist_ok=True)

        self._timeout = timeout
        self._work_dir: Path = work_dir

        self._functions = functions
        # Setup could take some time so we intentionally wait for the first code block to do it.
        if len(functions) > 0:
            self._setup_functions_complete = False
        else:
            self._setup_functions_complete = True

    def format_functions_for_prompt(self, prompt_template: str = FUNCTION_PROMPT_TEMPLATE) -> str:
        """(Experimental) Format the functions for a prompt.

        The template includes two variables:
        - `$module_name`: The module name.
        - `$functions`: The functions formatted as stubs with two newlines between each function.

        Args:
            prompt_template (str): The prompt template. Default is the class default.

        Returns:
            str: The formatted prompt.
        """

        template = Template(prompt_template)
        return template.substitute(
            module_name=self._functions_module,
            functions="\n\n".join([to_stub(func) for func in self._functions]),
        )

    @property
    def functions_module(self) -> str:
        """(Experimental) The module name for the functions."""
        return self._functions_module

    @property
    def functions(self) -> List[str]:
        raise NotImplementedError

    @property
    def timeout(self) -> int:
        """(Experimental) The timeout for code execution."""
        return self._timeout

    @property
    def work_dir(self) -> Path:
        """(Experimental) The working directory for the code execution."""
        return self._work_dir

    async def _setup_functions(self, cancellation_token: CancellationToken) -> None:
        func_file_content = build_python_functions_file(self._functions)
        func_file = self._work_dir / f"{self._functions_module}.py"
        func_file.write_text(func_file_content)

        # Collect requirements
        lists_of_packages = [x.python_packages for x in self._functions if isinstance(x, FunctionWithRequirements)]
        flattened_packages = [item for sublist in lists_of_packages for item in sublist]
        required_packages = list(set(flattened_packages))
        if len(required_packages) > 0:
            logging.info("Ensuring packages are installed in executor.")

            cmd_args = ["-m", "pip", "install"]
            cmd_args.extend(required_packages)

            task = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    *cmd_args,
                    cwd=self._work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )
            cancellation_token.link_future(task)
            try:
                proc = await task
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self._timeout)
            except asyncio.TimeoutError as e:
                raise ValueError("Pip install timed out") from e
            except asyncio.CancelledError as e:
                raise ValueError("Pip install was cancelled") from e

            if proc.returncode is not None and proc.returncode != 0:
                raise ValueError(f"Pip install failed. {stdout.decode()}, {stderr.decode()}")

        # Attempt to load the function file to check for syntax errors, imports etc.
        exec_result = await self._execute_code_dont_check_setup(
            [CodeBlock(code=func_file_content, language="python")], cancellation_token
        )

        if exec_result.exit_code != 0:
            raise ValueError(f"Functions failed to load: {exec_result.output}")

        self._setup_functions_complete = True

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CommandLineCodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.
            cancellation_token (CancellationToken): a token to cancel the operation

        Returns:
            CommandLineCodeResult: The result of the code execution."""

        if not self._setup_functions_complete:
            await self._setup_functions(cancellation_token)

        return await self._execute_code_dont_check_setup(code_blocks, cancellation_token)

    async def _execute_code_dont_check_setup(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CommandLineCodeResult:
        logs_all: str = ""
        file_names: List[Path] = []
        exitcode = 0
        for code_block in code_blocks:
            lang, code = code_block.language, code_block.code
            lang = lang.lower()

            code = silence_pip(code, lang)

            if lang in PYTHON_VARIANTS:
                lang = "python"

            if lang not in self.SUPPORTED_LANGUAGES:
                # In case the language is not supported, we return an error message.
                exitcode = 1
                logs_all += "\n" + f"unknown language {lang}"
                break

            try:
                # Check if there is a filename comment
                filename = get_file_name_from_content(code, self._work_dir)
            except ValueError:
                return CommandLineCodeResult(
                    exit_code=1,
                    output="Filename is not in the workspace",
                    code_file=None,
                )

            if filename is None:
                # create a file with an automatically generated name
                code_hash = md5(code.encode()).hexdigest()
                filename = f"tmp_code_{code_hash}.{'py' if lang.startswith('python') else lang}"

            written_file = (self._work_dir / filename).resolve()
            with written_file.open("w", encoding="utf-8") as f:
                f.write(code)
            file_names.append(written_file)

            program = sys.executable if lang.startswith("python") else lang_to_cmd(lang)
            # Wrap in a task to make it cancellable
            task = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    program,
                    str(written_file.absolute()),
                    cwd=self._work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )
            cancellation_token.link_future(task)
            try:
                proc = await task
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self._timeout)
                exitcode = proc.returncode or 0

            except asyncio.TimeoutError:
                logs_all += "\n Timeout"
                # Same exit code as the timeout command on linux.
                exitcode = 124
                break
            except asyncio.CancelledError:
                logs_all += "\n Cancelled"
                # TODO: which exit code? 125 is Operation Canceled
                exitcode = 125
                break

            self._running_cmd_task = None

            logs_all += stderr.decode()
            logs_all += stdout.decode()

            if exitcode != 0:
                break

        code_file = str(file_names[0]) if len(file_names) > 0 else None
        return CommandLineCodeResult(exit_code=exitcode, output=logs_all, code_file=code_file)

    async def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        warnings.warn(
            "Restarting local command line code executor is not supported. No action is taken.",
            stacklevel=2,
        )
