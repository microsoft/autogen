# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/local_commandline_code_executor.py
# Credit to original authors

import asyncio
from string import Template
from typing import Any, Callable, ClassVar, List, Optional, Protocol, Sequence, Union
from uuid import UUID, uuid4

import aiohttp
from azure.core.credentials import AccessToken

# from azure.mgmt.appcontainers import ContainerAppsAPIClient
from typing_extensions import ParamSpec

from ....core import CancellationToken
from .._base import CodeBlock, CodeExecutor, CodeResult
from .._func_with_reqs import (
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
    build_python_functions_file,
    to_stub,
)
from .utils import PYTHON_VARIANTS, get_required_packages, lang_to_cmd  # type: ignore

__all__ = ("AzureContainerCodeExecutor", "TokenProvider")

A = ParamSpec("A")


class TokenProvider(Protocol):
    def get_token(
        self, *scopes: str, claims: Optional[str] = None, tenant_id: Optional[str] = None, **kwargs: Any
    ) -> AccessToken: ...


class AzureContainerCodeExecutor(CodeExecutor):
    SUPPORTED_LANGUAGES: ClassVar[List[str]] = [
        "python",
    ]
    FUNCTION_PROMPT_TEMPLATE: ClassVar[str] = """You have access to the following user defined functions.

$functions"""

    def __init__(
        self,
        pool_management_endpoint: str,
        credential: TokenProvider,
        timeout: int = 60,
        functions: Sequence[
            Union[
                FunctionWithRequirements[Any, A],
                Callable[..., Any],
                FunctionWithRequirementsStr,
            ]
        ] = [],
        functions_module: str = "functions",
        persist_session: bool = False,
    ):
        """(Experimental) A code executor class that executes code through a an Azure
        Container Apps instance.

        **This will execute LLM generated code on an Azure dynamic code container.**

        The execution environment is similar to that of a jupyter notebook which allows for incremental code execution. The parameter functions are executed in order once at the beginning of each session. Each code block is then executed serially and in the order they are received. Each environment has a statically defined set of available packages which cannot be changed.
        Currently, attempting to use packages beyond what is available on the environment will result in an error. To get the list of supported packages, call the `get_available_packages` function.
        Currently the only supported language is Python.
        For Python code, use the language "python" for the code block.

        Args:
            pool_management_endpoint (str): The azure container apps dynamic sessions endpoint.
            credential (TokenProvider): An object that implements the get_token function.
            timeout (int): The timeout for the execution of any single code block. Default is 60.
            functions (List[Union[FunctionWithRequirements[Any, A], Callable[..., Any]]]): A list of functions that are available to the code executor. Default is an empty list.
            persist_session (bool): True - reuse the same azure session ID until restart() is called. False - Refresh the azure session ID for every call to execute_code(). Default is False.
        """

        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if not functions_module.isidentifier():
            raise ValueError("Module name must be a valid Python identifier")

        self._functions_module = functions_module

        self._timeout = timeout

        self._functions = functions
        self._func_code: str | None = None
        # Setup could take some time so we intentionally wait for the first code block to do it.
        if len(functions) > 0:
            self._setup_functions_complete = False
        else:
            self._setup_functions_complete = True

        self._pool_management_endpoint = pool_management_endpoint
        self._access_token: str | None = None
        self._persist_session = persist_session
        self._uuid: UUID = uuid4()
        self._available_packages: set[str] | None = None
        self._credential: TokenProvider = credential

    # TODO: expiration?
    def _ensure_access_token(self) -> None:
        if not self._access_token:
            scope = "https://dynamicsessions.io"
            self._access_token = self._credential.get_token(scope).token

    def format_functions_for_prompt(self, prompt_template: str = FUNCTION_PROMPT_TEMPLATE) -> str:
        """(Experimental) Format the functions for a prompt.

        The template includes one variable:
        - `$functions`: The functions formatted as stubs with two newlines between each function.

        Args:
            prompt_template (str): The prompt template. Default is the class default.

        Returns:
            str: The formatted prompt.
        """

        template = Template(prompt_template)
        return template.substitute(
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

    async def get_available_packages(self, cancellation_token: CancellationToken) -> set[str]:
        if self._available_packages is not None:
            return self._available_packages
        avail_pkgs = """
import pkg_resources\n[d.project_name for d in pkg_resources.working_set]
"""
        ret = await self._execute_code_dont_check_setup(
            [CodeBlock(code=avail_pkgs, language="python")], cancellation_token
        )
        if ret.exit_code != 0:
            raise ValueError(f"Failed to get list of available packages: {ret.output.strip()}")
        pkgs = ret.output.strip("[]")
        pkglist = pkgs.split(",\n")
        return {pkg.strip(" '") for pkg in pkglist}

    async def _populate_available_packages(self, cancellation_token: CancellationToken) -> None:
        self._available_packages = await self.get_available_packages(cancellation_token)

    async def _setup_functions(self, cancellation_token: CancellationToken) -> None:
        if not self._func_code:
            self._func_code = build_python_functions_file(self._functions)

            # Check required function imports and packages
            lists_of_packages = [x.python_packages for x in self._functions if isinstance(x, FunctionWithRequirements)]
            # Should we also be checking the imports?

            flattened_packages = [item for sublist in lists_of_packages for item in sublist]
            required_packages = set(flattened_packages)
            if self._available_packages is not None:
                missing_pkgs = set(required_packages - self._available_packages)
                if len(missing_pkgs) > 0:
                    raise ValueError(f"Packages unavailable in environment: {missing_pkgs}")

        # Attempt to load the function file to check for syntax errors, imports etc.
        exec_result = await self._execute_code_dont_check_setup(
            [CodeBlock(code=self._func_code, language="python")], cancellation_token
        )

        if exec_result.exit_code != 0:
            raise ValueError(f"Functions failed to load: {exec_result.output.strip()}")

        self._setup_functions_complete = True

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.
            cancellation_token (CancellationToken): a token to cancel the operation

        Returns:
            CodeResult: The result of the code execution."""
        if not self._persist_session:
            self.restart()
        if self._available_packages is None:
            await self._populate_available_packages(cancellation_token)
        if not self._setup_functions_complete:
            await self._setup_functions(cancellation_token)

        return await self._execute_code_dont_check_setup(code_blocks, cancellation_token)

    # The http call here should be replaced by an actual Azure client call once its available
    async def _execute_code_dont_check_setup(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        logs_all = ""
        exitcode = 0
        self._ensure_access_token()

        # TODO: Better to use the client auth system rather than headers
        headers = {"Authorization": f"Bearer {self._access_token}"}
        properties = {
            "identifier": str(self._uuid),
            "codeInputType": "inline",
            "executionType": "synchronous",
            "pythonCode": "",
            "timeoutInSeconds": self._timeout,
        }
        timeout = aiohttp.ClientTimeout(total=float(self._timeout))
        async with aiohttp.ClientSession(timeout=timeout) as client:
            for code_block in code_blocks:
                lang, code = code_block.language, code_block.code
                lang = lang.lower()

                if lang in PYTHON_VARIANTS:
                    lang = "python"

                if lang not in self.SUPPORTED_LANGUAGES:
                    # In case the language is not supported, we return an error message.
                    exitcode = 1
                    logs_all += "\n" + f"unknown language {lang}"
                    break

                if self._available_packages is not None:
                    req_pkgs = get_required_packages(code, lang)
                    missing_pkgs = set(req_pkgs - self._available_packages)
                    if len(missing_pkgs) > 0:
                        # In case the code requires packages that are not available in the environment
                        exitcode = 1
                        logs_all += "\n" + f"Python packages unavailable in environment: {missing_pkgs}"
                        break

                properties["pythonCode"] = code_block.code

                task = asyncio.create_task(
                    client.post(
                        self._pool_management_endpoint + "/python/execute",
                        headers=headers,
                        json={"properties": properties},
                    )
                )

                cancellation_token.link_future(task)
                try:
                    response = await asyncio.wait_for(task, self._timeout)
                    response.raise_for_status()
                    data = await response.json()
                    logs_all += data.get("stderr", "") + data.get("stdout", "")

                    if "Success" in data["status"]:
                        logs_all += str(data["result"])
                    elif "Failure" in data["status"]:
                        exitcode = 1
                    # This case is in the official code example https://github.com/Azure-Samples/container-apps-dynamic-sessions-samples/blob/dd2b3827bc8ea489b8f088654847239e2d51743f/autogen-python-webapi/aca_sessions_executor.py
                    # I have not seen this case actually occur before
                    if "error" in data:
                        logs_all += f"\n{data['error']}"
                        exitcode = 1

                except asyncio.TimeoutError as e:
                    logs_all += "\n Timeout"
                    # e.add_note is only in py 3.11+
                    raise asyncio.TimeoutError(logs_all) from e
                except asyncio.CancelledError as e:
                    logs_all += "\n Cancelled"
                    # e.add_note is only in py 3.11+
                    raise asyncio.CancelledError(logs_all) from e
                except aiohttp.ClientResponseError as e:
                    logs_all += "\nError while sending code block to endpoint"
                    raise ConnectionError(logs_all) from e

        return CodeResult(exit_code=exitcode, output=logs_all)

    def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        self._uuid = uuid4()
        self._setup_functions_complete = False
        self._access_token = None
        self._available_packages = None
