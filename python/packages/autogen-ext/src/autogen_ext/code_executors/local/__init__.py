# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/local_commandline_code_executor.py
# Credit to original authors

import asyncio
import logging
import os
import sys
import tempfile
import warnings
from hashlib import sha256
from pathlib import Path
from string import Template
from types import SimpleNamespace
from typing import Any, Callable, ClassVar, List, Optional, Sequence, Union

from autogen_core import CancellationToken, Component
from autogen_core.code_executor import CodeBlock, CodeExecutor, FunctionWithRequirements, FunctionWithRequirementsStr
from pydantic import BaseModel
from typing_extensions import ParamSpec, Self

from .._common import (
    PYTHON_VARIANTS,
    CommandLineCodeResult,
    build_python_functions_file,
    get_file_name_from_content,
    lang_to_cmd,
    silence_pip,
    to_stub,
)

__all__ = ("LocalCommandLineCodeExecutor",)

A = ParamSpec("A")


class LocalCommandLineCodeExecutorConfig(BaseModel):
    """Configuration for LocalCommandLineCodeExecutor"""

    timeout: int = 60
    work_dir: Optional[str] = None
    functions_module: str = "functions"


class LocalCommandLineCodeExecutor(CodeExecutor, Component[LocalCommandLineCodeExecutorConfig]):
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
    For shell scripts, use the language "bash", "shell", "sh", "pwsh", "powershell", or "ps1" for the code
    block.

    .. note::

        On Windows, the event loop policy must be set to `WindowsProactorEventLoopPolicy` to avoid issues with subprocesses.

        .. code-block:: python

            import sys
            import asyncio

            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    Args:
        timeout (int): The timeout for the execution of any single code block. Default is 60.
        work_dir (str): The working directory for the code execution. If None,
            a default working directory will be used. The default working directory is a temporary directory.
        functions (List[Union[FunctionWithRequirements[Any, A], Callable[..., Any]]]): A list of functions that are available to the code executor. Default is an empty list.
        functions_module (str, optional): The name of the module that will be created to store the functions. Defaults to "functions".
        virtual_env_context (Optional[SimpleNamespace], optional): The virtual environment context. Defaults to None.

    .. note::
        Using the current directory (".") as working directory is deprecated. Using it will raise a deprecation warning.


    Example:

    How to use `LocalCommandLineCodeExecutor` with a virtual environment different from the one used to run the autogen application:
    Set up a virtual environment using the `venv` module, and pass its context to the initializer of `LocalCommandLineCodeExecutor`. This way, the executor will run code within the new environment.

        .. code-block:: python

            import venv
            from pathlib import Path
            import asyncio

            from autogen_core import CancellationToken
            from autogen_core.code_executor import CodeBlock
            from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


            async def example():
                work_dir = Path("coding")
                work_dir.mkdir(exist_ok=True)

                venv_dir = work_dir / ".venv"
                venv_builder = venv.EnvBuilder(with_pip=True)
                venv_builder.create(venv_dir)
                venv_context = venv_builder.ensure_directories(venv_dir)

                local_executor = LocalCommandLineCodeExecutor(work_dir=work_dir, virtual_env_context=venv_context)
                await local_executor.execute_code_blocks(
                    code_blocks=[
                        CodeBlock(language="bash", code="pip install matplotlib"),
                    ],
                    cancellation_token=CancellationToken(),
                )


            asyncio.run(example())

    """

    component_config_schema = LocalCommandLineCodeExecutorConfig
    component_provider_override = "autogen_ext.code_executors.local.LocalCommandLineCodeExecutor"

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
        work_dir: Optional[Union[Path, str]] = None,
        functions: Sequence[
            Union[
                FunctionWithRequirements[Any, A],
                Callable[..., Any],
                FunctionWithRequirementsStr,
            ]
        ] = [],
        functions_module: str = "functions",
        virtual_env_context: Optional[SimpleNamespace] = None,
    ):
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        self._work_dir: Optional[Path] = None
        if work_dir is not None:
            # Check if user provided work_dir is the current directory and warn if so.
            if Path(work_dir).resolve() == Path.cwd().resolve():
                warnings.warn(
                    "Using the current directory as work_dir is deprecated.",
                    DeprecationWarning,
                    stacklevel=2,
                )
            if isinstance(work_dir, str):
                self._work_dir = Path(work_dir)
            else:
                self._work_dir = work_dir
            self._work_dir.mkdir(exist_ok=True)

        if not functions_module.isidentifier():
            raise ValueError("Module name must be a valid Python identifier")

        self._functions_module = functions_module

        self._timeout = timeout

        self._functions = functions
        # Setup could take some time so we intentionally wait for the first code block to do it.
        if len(functions) > 0:
            self._setup_functions_complete = False
        else:
            self._setup_functions_complete = True

        self._virtual_env_context: Optional[SimpleNamespace] = virtual_env_context

        self._temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None
        self._started = False

        # Check the current event loop policy if on windows.
        if sys.platform == "win32":
            current_policy = asyncio.get_event_loop_policy()
            if hasattr(asyncio, "WindowsProactorEventLoopPolicy") and not isinstance(
                current_policy, asyncio.WindowsProactorEventLoopPolicy
            ):
                warnings.warn(
                    "The current event loop policy is not WindowsProactorEventLoopPolicy. "
                    "This may cause issues with subprocesses. "
                    "Try setting the event loop policy to WindowsProactorEventLoopPolicy. "
                    "For example: `asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())`. "
                    "See https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.ProactorEventLoop.",
                    stacklevel=2,
                )

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
        if self._work_dir is not None:
            return self._work_dir
        else:
            # Automatically create temp directory if not exists
            if self._temp_dir is None:
                self._temp_dir = tempfile.TemporaryDirectory()
                self._started = True
            return Path(self._temp_dir.name)

    async def _setup_functions(self, cancellation_token: CancellationToken) -> None:
        func_file_content = build_python_functions_file(self._functions)
        func_file = self.work_dir / f"{self._functions_module}.py"
        func_file.write_text(func_file_content)

        # Collect requirements
        lists_of_packages = [x.python_packages for x in self._functions if isinstance(x, FunctionWithRequirements)]
        flattened_packages = [item for sublist in lists_of_packages for item in sublist]
        required_packages = list(set(flattened_packages))
        if len(required_packages) > 0:
            logging.info("Ensuring packages are installed in executor.")

            cmd_args = ["-m", "pip", "install"]
            cmd_args.extend(required_packages)

            if self._virtual_env_context:
                py_executable = self._virtual_env_context.env_exe
            else:
                py_executable = sys.executable

            task = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    py_executable,
                    *cmd_args,
                    cwd=self.work_dir,
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
        """
        Execute the provided code blocks in the local command line without re-checking setup.
        Returns a CommandLineCodeResult indicating success or failure.
        """
        logs_all: str = ""
        file_names: List[Path] = []
        exitcode = 0

        for code_block in code_blocks:
            lang, code = code_block.language, code_block.code
            lang = lang.lower()

            # Remove pip output where possible
            code = silence_pip(code, lang)

            # Normalize python variants to "python"
            if lang in PYTHON_VARIANTS:
                lang = "python"

            # Abort if not supported
            if lang not in self.SUPPORTED_LANGUAGES:
                exitcode = 1
                logs_all += "\n" + f"unknown language {lang}"
                break

            # Try extracting a filename (if present)
            try:
                filename = get_file_name_from_content(code, self.work_dir)
            except ValueError:
                return CommandLineCodeResult(
                    exit_code=1,
                    output="Filename is not in the workspace",
                    code_file=None,
                )

            # If no filename is found, create one
            if filename is None:
                code_hash = sha256(code.encode()).hexdigest()
                if lang.startswith("python"):
                    ext = "py"
                elif lang in ["pwsh", "powershell", "ps1"]:
                    ext = "ps1"
                else:
                    ext = lang

                filename = f"tmp_code_{code_hash}.{ext}"

            written_file = (self.work_dir / filename).resolve()
            with written_file.open("w", encoding="utf-8") as f:
                f.write(code)
            file_names.append(written_file)

            # Build environment
            env = os.environ.copy()
            if self._virtual_env_context:
                virtual_env_bin_abs_path = os.path.abspath(self._virtual_env_context.bin_path)
                env["PATH"] = f"{virtual_env_bin_abs_path}{os.pathsep}{env['PATH']}"

            # Decide how to invoke the script
            if lang == "python":
                program = (
                    os.path.abspath(self._virtual_env_context.env_exe) if self._virtual_env_context else sys.executable
                )
                extra_args = [str(written_file.absolute())]
            else:
                # Get the appropriate command for the language
                program = lang_to_cmd(lang)

                # Special handling for PowerShell
                if program == "pwsh":
                    extra_args = [
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(written_file.absolute()),
                    ]
                else:
                    # Shell commands (bash, sh, etc.)
                    extra_args = [str(written_file.absolute())]

            # Create a subprocess and run
            task = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    program,
                    *extra_args,
                    cwd=self.work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            )
            cancellation_token.link_future(task)

            proc = None  # Track the process
            try:
                proc = await task
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self._timeout)
                exitcode = proc.returncode or 0
            except asyncio.TimeoutError:
                logs_all += "\nTimeout"
                exitcode = 124
                if proc:
                    proc.terminate()
                    await proc.wait()  # Ensure process is fully dead
                break
            except asyncio.CancelledError:
                logs_all += "\nCancelled"
                exitcode = 125
                if proc:
                    proc.terminate()
                    await proc.wait()
                break

            logs_all += stderr.decode()
            logs_all += stdout.decode()

            if exitcode != 0:
                break

        code_file = str(file_names[0]) if file_names else None
        return CommandLineCodeResult(exit_code=exitcode, output=logs_all, code_file=code_file)

    async def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        warnings.warn(
            "Restarting local command line code executor is not supported. No action is taken.",
            stacklevel=2,
        )

    async def start(self) -> None:
        """(Experimental) Start the code executor."""
        if self._work_dir is None and self._temp_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory()
        self._started = True

    async def stop(self) -> None:
        """(Experimental) Stop the code executor."""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
        self._started = False
        pass

    def _to_config(self) -> LocalCommandLineCodeExecutorConfig:
        if self._functions:
            logging.info("Functions will not be included in serialized configuration")
        if self._virtual_env_context:
            logging.info("Virtual environment context will not be included in serialized configuration")

        return LocalCommandLineCodeExecutorConfig(
            timeout=self._timeout,
            work_dir=str(self.work_dir),
            functions_module=self._functions_module,
        )

    @classmethod
    def _from_config(cls, config: LocalCommandLineCodeExecutorConfig) -> Self:
        return cls(
            timeout=config.timeout,
            work_dir=Path(config.work_dir) if config.work_dir is not None else None,
            functions_module=config.functions_module,
        )
