from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import sys
import tempfile
import warnings
from hashlib import sha256
from pathlib import Path
from string import Template
from types import SimpleNamespace
from typing import Any, Callable, ClassVar, List, Optional, Sequence, Union

from autogen_core import CancellationToken, Component
from autogen_core.code_executor import (
    CodeBlock,
    CodeExecutor,
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
)
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

logger = logging.getLogger(__name__)

A = ParamSpec("A")


class VettoCommandLineCodeExecutorConfig(BaseModel):
    """Configuration schema for VettoCommandLineCodeExecutor."""

    timeout: int = 60
    work_dir: Optional[str] = None
    net: str = "off"
    allowed_domains: Optional[List[str]] = None
    allow_write: Optional[List[str]] = None
    allow_read: Optional[List[str]] = None
    memory_limit: Optional[str] = None
    vetto_binary: Optional[str] = None
    allow_fallback: bool = False
    functions_module: str = "functions"
    cleanup_temp_files: bool = True


class VettoCommandLineCodeExecutor(CodeExecutor, Component[VettoCommandLineCodeExecutorConfig]):
    """Code executor running code within an unprivileged kernel-level Vetto sandbox.

    Vetto provides daemon-less, rootless sandbox boundaries (Linux Landlock LSM ABI 1-6,
    namespaces, cgroups v2, macOS Seatbelt, Windows LPAC) with sub-4ms cold startup overhead.

    Args:
        timeout: Execution timeout in seconds for any single code block. Defaults to 60.
        work_dir: Workspace directory for code containment. Defaults to a temporary directory.
        net: Network isolation policy: 'off' (full isolation), 'allowlist', or 'host'. Defaults to 'off'.
        allowed_domains: List of permitted domains when net='allowlist'. Defaults to None.
        allow_write: Additional file or directory paths permitted for write access. Defaults to None.
        allow_read: Additional file or directory paths permitted for read-only access. Defaults to None.
        memory_limit: Memory limit ceiling (e.g. '512MB', '1GB'). Defaults to None.
        vetto_binary: Explicit path to the vetto binary. Defaults to searching PATH and standard paths.
        allow_fallback: If True, falls back to local execution when vetto binary is missing. Defaults to False.
        functions: Sequence of functions made available to the code execution context. Defaults to empty.
        functions_module: Python module name storing functions. Defaults to 'functions'.
        cleanup_temp_files: Whether to remove generated temporary code files. Defaults to True.
        virtual_env_context: Optional virtual environment context. Defaults to None.
    """

    component_config_schema = VettoCommandLineCodeExecutorConfig
    component_provider_override = "autogen_ext.code_executors.vetto.VettoCommandLineCodeExecutor"

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = [
        "bash",
        "shell",
        "sh",
        "pwsh",
        "powershell",
        "ps1",
        "python",
    ]
    FUNCTION_PROMPT_TEMPLATE: ClassVar[str] = (
        "You have access to the following user defined functions. They can be accessed from the module "
        "called `$module_name` by their function names.\n\n"
        "For example, if there was a function called `foo` you could import it by writing `from $module_name import foo`\n\n"
        "$functions"
    )

    def __init__(
        self,
        timeout: int = 60,
        work_dir: Optional[Union[Path, str]] = None,
        net: str = "off",
        allowed_domains: Optional[List[str]] = None,
        allow_write: Optional[List[str]] = None,
        allow_read: Optional[List[str]] = None,
        memory_limit: Optional[str] = None,
        vetto_binary: Optional[str] = None,
        allow_fallback: bool = False,
        functions: Sequence[
            Union[
                FunctionWithRequirements[Any, A],
                Callable[..., Any],
                FunctionWithRequirementsStr,
            ]
        ] = [],
        functions_module: str = "functions",
        cleanup_temp_files: bool = True,
        virtual_env_context: Optional[SimpleNamespace] = None,
    ):
        """Initialize the Vetto command line code executor."""
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")
        self._timeout = timeout

        self._net = net
        self._allowed_domains = allowed_domains
        self._allow_write = allow_write
        self._allow_read = allow_read
        self._memory_limit = memory_limit
        self._vetto_binary = vetto_binary
        self._allow_fallback = allow_fallback

        self._work_dir: Optional[Path] = None
        if work_dir is not None:
            if isinstance(work_dir, str):
                self._work_dir = Path(work_dir)
            else:
                self._work_dir = work_dir
            self._work_dir.mkdir(parents=True, exist_ok=True)

        self._functions = functions
        if len(functions) > 0:
            self._setup_functions_complete = False
        else:
            self._setup_functions_complete = True

        if not functions_module.isidentifier():
            raise ValueError("Module name must be a valid Python identifier")
        self._functions_module = functions_module

        self._cleanup_temp_files = cleanup_temp_files
        self._virtual_env_context: Optional[SimpleNamespace] = virtual_env_context
        self._temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None

    def _resolve_vetto_binary(self) -> Optional[str]:
        """Resolve the executable path to the Vetto binary.

        Returns:
            Resolved path string or None if not found on the host system.
        """
        if self._vetto_binary and os.path.isfile(self._vetto_binary) and os.access(self._vetto_binary, os.X_OK):
            return self._vetto_binary

        env_path = os.getenv("VETTO_PATH")
        if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path

        found = shutil.which("vetto")
        if found:
            return found

        candidates = [
            os.path.expanduser("~/.cargo/bin/vetto"),
            "/usr/local/bin/vetto",
            "/usr/bin/vetto",
        ]
        for path in candidates:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        return None

    def _build_command(
        self,
        command_args: List[str],
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> List[str]:
        """Build the wrapped execution command with Vetto sandbox boundaries.

        Args:
            command_args: Original command arguments to run.
            cwd: Effective working directory path.
            timeout: Command timeout in seconds.

        Returns:
            Prefixed command arguments vector.

        Raises:
            RuntimeError: If vetto binary is not found and allow_fallback is False.
        """
        vetto_bin = self._resolve_vetto_binary()
        if not vetto_bin:
            if not self._allow_fallback:
                raise RuntimeError(
                    "Vetto binary not found. Install via 'cargo install vetto' "
                    "or 'npm install -g @shledery/vetto', set VETTO_PATH, or "
                    "configure allow_fallback=True."
                )
            return command_args

        effective_cwd = cwd or self.work_dir
        resolved_cwd = str(effective_cwd.resolve())

        run_args = [vetto_bin, "run", f"--net={self._net}"]

        effective_timeout = timeout if timeout is not None else self._timeout
        if effective_timeout:
            run_args.extend(["--timeout", str(effective_timeout)])

        if self._memory_limit:
            run_args.extend(["--memory", self._memory_limit])

        run_args.extend(["--allow-write", resolved_cwd])

        if self._allow_write:
            for p in self._allow_write:
                run_args.extend(["--allow-write", str(Path(p).resolve())])

        if self._allow_read:
            for p in self._allow_read:
                run_args.extend(["--allow-read", str(Path(p).resolve())])

        if self._net == "allowlist" and self._allowed_domains:
            for domain in self._allowed_domains:
                run_args.extend(["--allow-domain", domain])

        run_args.append("--")
        run_args.extend(command_args)
        return run_args

    def format_functions_for_prompt(self, prompt_template: str = FUNCTION_PROMPT_TEMPLATE) -> str:
        """Format configured functions as prompt stubs.

        Args:
            prompt_template: Template string containing $module_name and $functions.

        Returns:
            Formatted prompt text.
        """
        template = Template(prompt_template)
        return template.substitute(
            module_name=self._functions_module,
            functions="\n\n".join([to_stub(func) for func in self._functions]),
        )

    @property
    def timeout(self) -> int:
        """Execution timeout in seconds."""
        return self._timeout

    @property
    def net(self) -> str:
        """Configured network isolation mode."""
        return self._net

    @property
    def work_dir(self) -> Path:
        """Working directory used for code execution."""
        if self._work_dir is not None:
            return self._work_dir
        if self._temp_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory()
        return Path(self._temp_dir.name)

    @property
    def functions(self) -> List[str]:
        """List of function names available to the executor."""
        return [func.__name__ for func in self._functions]

    async def _setup_functions(self, cancellation_token: CancellationToken) -> None:
        """Generate and write the Python functions module to the working directory.

        Args:
            cancellation_token: Token to monitor for cancellation requests.

        Raises:
            ValueError: If writing the functions module fails.
        """
        functions_file_content = build_python_functions_file(self._functions)
        functions_module_file = self.work_dir / f"{self._functions_module}.py"

        with open(functions_module_file, "w", encoding="utf-8") as f:
            f.write(functions_file_content)

        code_block = CodeBlock(
            code=f"import {self._functions_module}",
            language="python",
        )
        exec_result = await self._execute_code_dont_check_setup([code_block], cancellation_token)

        if exec_result.exit_code != 0:
            raise ValueError(f"Functions failed to load: {exec_result.output}")

        self._setup_functions_complete = True

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CommandLineCodeResult:
        """Execute code blocks within the Vetto sandbox and return the execution result.

        Args:
            code_blocks: Ordered list of code blocks to execute.
            cancellation_token: Token to cancel execution.

        Returns:
            CommandLineCodeResult containing exit code, output logs, and code file path.
        """
        if not self._setup_functions_complete:
            await self._setup_functions(cancellation_token)

        return await self._execute_code_dont_check_setup(code_blocks, cancellation_token)

    async def _execute_code_dont_check_setup(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CommandLineCodeResult:
        """Execute code blocks inside the Vetto sandbox without re-checking function setup.

        Args:
            code_blocks: Code blocks to execute.
            cancellation_token: Cancellation token.

        Returns:
            CommandLineCodeResult with execution results.
        """
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
                exitcode = 1
                logs_all += "\n" + f"unknown language {lang}"
                break

            try:
                filename = get_file_name_from_content(code, self.work_dir)
            except ValueError:
                return CommandLineCodeResult(
                    exit_code=1,
                    output="Filename is not in the workspace",
                    code_file=None,
                )

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

            env = os.environ.copy()
            if self._virtual_env_context:
                virtual_env_bin_abs_path = os.path.abspath(self._virtual_env_context.bin_path)
                env["PATH"] = f"{virtual_env_bin_abs_path}{os.pathsep}{env['PATH']}"

            if lang == "python":
                program = (
                    os.path.abspath(self._virtual_env_context.env_exe)
                    if self._virtual_env_context
                    else sys.executable
                )
                raw_args = [program, str(written_file.absolute())]
            else:
                program = lang_to_cmd(lang)
                if program == "pwsh":
                    raw_args = [
                        program,
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(written_file.absolute()),
                    ]
                else:
                    raw_args = [program, str(written_file.absolute())]

            sandboxed_args = self._build_command(raw_args, cwd=self.work_dir, timeout=self._timeout)

            # Preexec for process group isolation on POSIX
            kwargs: dict[str, Any] = {
                "cwd": str(self.work_dir),
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
                "env": env,
            }
            if hasattr(os, "setsid"):
                kwargs["preexec_fn"] = os.setsid

            task = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    sandboxed_args[0],
                    *sandboxed_args[1:],
                    **kwargs,
                )
            )
            cancellation_token.link_future(task)

            proc = None
            try:
                proc = await task
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self._timeout)
                exitcode = proc.returncode or 0
            except asyncio.TimeoutError:
                logs_all += "\nTimeout"
                exitcode = 124
                if proc:
                    self._kill_process_tree(proc)
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                break
            except asyncio.CancelledError:
                logs_all += "\nCancelled"
                exitcode = 125
                if proc:
                    self._kill_process_tree(proc)
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                break

            logs_all += stderr.decode("utf-8", errors="replace")
            logs_all += stdout.decode("utf-8", errors="replace")

            if exitcode != 0:
                break

        code_file = str(file_names[0]) if file_names else None
        code_result = CommandLineCodeResult(exit_code=exitcode, output=logs_all, code_file=code_file)

        if self._cleanup_temp_files:
            for file in file_names:
                try:
                    file.unlink(missing_ok=True)
                except OSError as error:
                    logger.debug("Failed to delete temporary file %s: %s", file, error)

        return code_result

    def _kill_process_tree(self, proc: asyncio.subprocess.Process) -> None:
        """Terminate the process and its descendants cleanly using process group signaling.

        Args:
            proc: Subprocess instance to terminate.
        """
        if hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
                return
            except OSError:
                pass
        try:
            proc.kill()
        except OSError:
            pass

    async def restart(self) -> None:
        """Reset temporary state of the code executor."""
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None

    def _to_config(self) -> VettoCommandLineCodeExecutorConfig:
        """Serialize instance state to a configuration model.

        Returns:
            VettoCommandLineCodeExecutorConfig instance.
        """
        return VettoCommandLineCodeExecutorConfig(
            timeout=self._timeout,
            work_dir=str(self._work_dir) if self._work_dir else None,
            net=self._net,
            allowed_domains=self._allowed_domains,
            allow_write=self._allow_write,
            allow_read=self._allow_read,
            memory_limit=self._memory_limit,
            vetto_binary=self._vetto_binary,
            allow_fallback=self._allow_fallback,
            functions_module=self._functions_module,
            cleanup_temp_files=self._cleanup_temp_files,
        )

    @classmethod
    def _from_config(cls, config: VettoCommandLineCodeExecutorConfig) -> Self:
        """Instantiate an executor from a configuration model.

        Args:
            config: Configuration schema instance.

        Returns:
            Configured VettoCommandLineCodeExecutor instance.
        """
        return cls(
            timeout=config.timeout,
            work_dir=config.work_dir,
            net=config.net,
            allowed_domains=config.allowed_domains,
            allow_write=config.allow_write,
            allow_read=config.allow_read,
            memory_limit=config.memory_limit,
            vetto_binary=config.vetto_binary,
            allow_fallback=config.allow_fallback,
            functions_module=config.functions_module,
            cleanup_temp_files=config.cleanup_temp_files,
        )
