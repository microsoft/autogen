# Credit to original authors

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any, Callable, ClassVar, List, Optional, Protocol, Sequence, Union
from uuid import uuid4

import aiohttp

# async functions shouldn't use open()
from anyio import open_file
from autogen_core import CancellationToken
from autogen_core.code_executor import (
    CodeBlock,
    CodeExecutor,
    CodeResult,
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
)
from typing_extensions import ParamSpec

from .._common import build_python_functions_file, get_required_packages, to_stub

if TYPE_CHECKING:
    from azure.core.credentials import AccessToken

PYTHON_VARIANTS = ["python", "Python", "py"]

__all__ = ("ACADynamicSessionsCodeExecutor", "TokenProvider")

A = ParamSpec("A")


class TokenProvider(Protocol):
    def get_token(
        self, *scopes: str, claims: Optional[str] = None, tenant_id: Optional[str] = None, **kwargs: Any
    ) -> AccessToken: ...


class ACADynamicSessionsCodeExecutor(CodeExecutor):
    """(Experimental) A code executor class that executes code through a an Azure
    Container Apps Dynamic Sessions instance.

    .. note::

        This class requires the :code:`azure` extra for the :code:`autogen-ext` package:

        .. code-block:: bash

            pip install "autogen-ext[azure]==0.4.0.dev12"

    .. caution::

        **This will execute LLM generated code on an Azure dynamic code container.**

    The execution environment is similar to that of a jupyter notebook which allows for incremental code execution. The parameter functions are executed in order once at the beginning of each session. Each code block is then executed serially and in the order they are received. Each environment has a statically defined set of available packages which cannot be changed.
    Currently, attempting to use packages beyond what is available on the environment will result in an error. To get the list of supported packages, call the `get_available_packages` function.
    Currently the only supported language is Python.
    For Python code, use the language "python" for the code block.

    Args:
        pool_management_endpoint (str): The azure container apps dynamic sessions endpoint.
        credential (TokenProvider): An object that implements the get_token function.
        timeout (int): The timeout for the execution of any single code block. Default is 60.
        work_dir (str): The working directory for the code execution. If None,
            a default working directory will be used. The default working
            directory is the current directory ".".
        functions (List[Union[FunctionWithRequirements[Any, A], Callable[..., Any]]]): A list of functions that are available to the code executor. Default is an empty list.
    """

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = [
        "python",
    ]
    FUNCTION_PROMPT_TEMPLATE: ClassVar[str] = """You have access to the following user defined functions.

$functions"""

    _AZURE_API_VER = "2024-02-02-preview"

    def __init__(
        self,
        pool_management_endpoint: str,
        credential: TokenProvider,
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
        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)

        if not functions_module.isidentifier():
            raise ValueError("Module name must be a valid Python identifier")

        self._functions_module = functions_module

        work_dir.mkdir(exist_ok=True)
        self._work_dir: Path = work_dir

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
        self._session_id: str = str(uuid4())
        self._available_packages: set[str] | None = None
        self._credential: TokenProvider = credential
        # cwd needs to be set to /mnt/data to properly read uploaded files and download written files
        self._setup_cwd_complete = False

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

    @property
    def work_dir(self) -> Path:
        """(Experimental) The working directory for the code execution."""
        return self._work_dir

    def _construct_url(self, path: str) -> str:
        endpoint = self._pool_management_endpoint
        if not endpoint.endswith("/"):
            endpoint += "/"
        url = endpoint + f"{path}?api-version={self._AZURE_API_VER}&identifier={self._session_id}"
        return url

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

    async def _setup_cwd(self, cancellation_token: CancellationToken) -> None:
        # Change the cwd to /mnt/data to properly have access to uploaded files
        exec_result = await self._execute_code_dont_check_setup(
            [CodeBlock(code="import os; os.chdir('/mnt/data')", language="python")], cancellation_token
        )

        if exec_result.exit_code != 0:
            raise ValueError("Failed to set up Azure container working directory")
        self._setup_cwd_complete = True

    async def get_file_list(self, cancellation_token: CancellationToken) -> List[str]:
        self._ensure_access_token()
        timeout = aiohttp.ClientTimeout(total=float(self._timeout))
        headers = {
            "Authorization": f"Bearer {self._access_token}",
        }
        url = self._construct_url("files")
        async with aiohttp.ClientSession(timeout=timeout) as client:
            task = asyncio.create_task(
                client.get(
                    url,
                    headers=headers,
                )
            )
            cancellation_token.link_future(task)
            try:
                resp = await task
                resp.raise_for_status()
                data = await resp.json()
            except asyncio.TimeoutError as e:
                # e.add_note is only in py 3.11+
                raise asyncio.TimeoutError("Timeout getting file list") from e
            except asyncio.CancelledError as e:
                # e.add_note is only in py 3.11+
                raise asyncio.CancelledError("File list retrieval cancelled") from e
            except aiohttp.ClientResponseError as e:
                raise ConnectionError("Error while getting file list") from e

        values = data["value"]
        file_info_list: List[str] = []
        for value in values:
            file = value["properties"]
            file_info_list.append(file["filename"])
        return file_info_list

    async def upload_files(self, files: List[Union[Path, str]], cancellation_token: CancellationToken) -> None:
        self._ensure_access_token()
        # TODO: Better to use the client auth system rather than headers
        headers = {"Authorization": f"Bearer {self._access_token}"}
        url = self._construct_url("files/upload")
        timeout = aiohttp.ClientTimeout(total=float(self._timeout))
        async with aiohttp.ClientSession(timeout=timeout) as client:
            for file in files:
                file_path = os.path.join(self._work_dir, file)
                if not os.path.isfile(file_path):
                    # TODO: what to do here?
                    raise FileNotFoundError(f"{file} does not exist")

                data = aiohttp.FormData()
                async with await open_file(file_path, "rb") as f:
                    data.add_field(
                        "file",
                        f,
                        filename=os.path.basename(file_path),
                        content_type="application/octet-stream",
                    )

                    task = asyncio.create_task(
                        client.post(
                            url,
                            headers=headers,
                            data=data,
                        )
                    )

                    cancellation_token.link_future(task)
                    try:
                        resp = await task
                        resp.raise_for_status()

                    except asyncio.TimeoutError as e:
                        # e.add_note is only in py 3.11+
                        raise asyncio.TimeoutError("Timeout uploading files") from e
                    except asyncio.CancelledError as e:
                        # e.add_note is only in py 3.11+
                        raise asyncio.CancelledError("Uploading files cancelled") from e
                    except aiohttp.ClientResponseError as e:
                        raise ConnectionError("Error while uploading files") from e

    async def download_files(self, files: List[Union[Path, str]], cancellation_token: CancellationToken) -> List[str]:
        self._ensure_access_token()
        available_files = await self.get_file_list(cancellation_token)
        # TODO: Better to use the client auth system rather than headers
        headers = {"Authorization": f"Bearer {self._access_token}"}
        timeout = aiohttp.ClientTimeout(total=float(self._timeout))
        local_paths: List[str] = []
        async with aiohttp.ClientSession(timeout=timeout) as client:
            for file in files:
                if file not in available_files:
                    # TODO: what's the right thing to do here?
                    raise FileNotFoundError(f"{file} does not exist")

                url = self._construct_url(f"files/content/{file}")

                task = asyncio.create_task(
                    client.get(
                        url,
                        headers=headers,
                    )
                )
                cancellation_token.link_future(task)
                try:
                    resp = await task
                    resp.raise_for_status()
                    local_path = os.path.join(self._work_dir, file)
                    local_paths.append(local_path)
                    async with await open_file(local_path, "wb") as f:
                        await f.write(await resp.read())
                except asyncio.TimeoutError as e:
                    # e.add_note is only in py 3.11+
                    raise asyncio.TimeoutError("Timeout downloading files") from e
                except asyncio.CancelledError as e:
                    # e.add_note is only in py 3.11+
                    raise asyncio.CancelledError("Downloading files cancelled") from e
                except aiohttp.ClientResponseError as e:
                    raise ConnectionError("Error while downloading files") from e
        return local_paths

    async def execute_code_blocks(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.
            cancellation_token (CancellationToken): a token to cancel the operation
            input_files (Optional[Union[Path, str]]): Any files the code blocks will need to access

        Returns:
            CodeResult: The result of the code execution."""

        self._ensure_access_token()
        if self._available_packages is None:
            await self._populate_available_packages(cancellation_token)
        if not self._setup_functions_complete:
            await self._setup_functions(cancellation_token)
        if not self._setup_cwd_complete:
            await self._setup_cwd(cancellation_token)

        return await self._execute_code_dont_check_setup(code_blocks, cancellation_token)

    # The http call here should be replaced by an actual Azure client call once its available
    async def _execute_code_dont_check_setup(
        self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken
    ) -> CodeResult:
        logs_all = ""
        exitcode = 0

        # TODO: Better to use the client auth system rather than headers
        assert self._access_token is not None
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        properties = {
            "codeInputType": "inline",
            "executionType": "synchronous",
            "code": "",  # Filled in later
        }
        url = self._construct_url("code/execute")
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

                properties["code"] = code_block.code

                task = asyncio.create_task(
                    client.post(
                        url,
                        headers=headers,
                        json={"properties": properties},
                    )
                )

                cancellation_token.link_future(task)
                try:
                    response = await task
                    response.raise_for_status()
                    data = await response.json()
                    data = data["properties"]
                    logs_all += data.get("stderr", "") + data.get("stdout", "")
                    if "Success" in data["status"]:
                        logs_all += str(data["result"])
                    elif "Failure" in data["status"]:
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

    async def restart(self) -> None:
        """(Experimental) Restart the code executor."""
        self._session_id = str(uuid4())
        self._setup_functions_complete = False
        self._access_token = None
        self._available_packages = None
        self._setup_cwd_complete = False
