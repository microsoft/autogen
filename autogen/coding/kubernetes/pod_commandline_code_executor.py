from __future__ import annotations

import atexit
import importlib
import sys
import textwrap
import uuid
from hashlib import md5
from pathlib import Path
from time import sleep
from types import TracebackType
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

client = importlib.import_module("kubernetes.client")
config = importlib.import_module("kubernetes.config")
ApiException = importlib.import_module("kubernetes.client.rest").ApiException
stream = importlib.import_module("kubernetes.stream").stream

from ...code_utils import TIMEOUT_MSG, _cmd
from ..base import CodeBlock, CodeExecutor, CodeExtractor, CommandLineCodeResult
from ..markdown_code_extractor import MarkdownCodeExtractor
from ..utils import _get_file_name_from_content, silence_pip

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class PodCommandLineCodeExecutor(CodeExecutor):
    DEFAULT_EXECUTION_POLICY: ClassVar[Dict[str, bool]] = {
        "bash": True,
        "shell": True,
        "sh": True,
        "pwsh": False,
        "powershell": False,
        "ps1": False,
        "python": True,
        "javascript": False,
        "html": False,
        "css": False,
    }
    LANGUAGE_ALIASES: ClassVar[Dict[str, str]] = {
        "py": "python",
        "js": "javascript",
    }
    LANGUAGE_FILE_EXTENSION: ClassVar[Dict[str, str]] = {
        "python": "py",
        "javascript": "js",
        "bash": "sh",
        "shell": "sh",
        "sh": "sh",
    }

    def __init__(
        self,
        image: str = "python:3-slim",
        pod_name: Optional[str] = None,
        namespace: Optional[str] = None,
        pod_spec: Optional[client.V1Pod] = None,  # type: ignore
        container_name: Optional[str] = "autogen-code-exec",
        timeout: int = 60,
        work_dir: Union[Path, str] = Path("/workspace"),
        kube_config_file: Optional[str] = None,
        stop_container: bool = True,
        execution_policies: Optional[Dict[str, bool]] = None,
    ):
        """(Experimental) A code executor class that executes code through
        a command line environment in a kubernetes pod.

        The executor first saves each code block in a file in the working
        directory, and then executes the code file in the container.
        The executor executes the code blocks in the order they are received.
        Currently, the executor only supports Python and shell scripts.
        For Python code, use the language "python" for the code block.
        For shell scripts, use the language "bash", "shell", or "sh" for the code
        block.

        Args:
            image (_type_, optional): Docker image to use for code execution.
                Defaults to "python:3-slim".
            pod_name (Optional[str], optional): Name of the kubernetes pod
                which is created. If None, will autogenerate a name. Defaults to None.
            namespace (Optional[str], optional): Namespace of kubernetes pod
                which is created. If None, will use current namespace of this instance
            pod_spec (Optional[client.V1Pod], optional): Specification of kubernetes pod.
                custom pod spec can be provided with this param.
                if pod_spec is provided, params above(image, pod_name, namespace) are neglected.
            container_name (Optional[str], optional): Name of the container where code block will be
                executed. if pod_spec param is provided, container_name must be provided also.
            timeout (int, optional): The timeout for code execution. Defaults to 60.
            work_dir (Union[Path, str], optional): The working directory for the code
                execution. Defaults to Path("/workspace").
            kube_config_file (Optional[str], optional): kubernetes configuration file path.
                If None, will use KUBECONFIG environment variables or service account token(incluster config)
            stop_container (bool, optional): If true, will automatically stop the
                container when stop is called, when the context manager exits or when
                the Python process exits with atext. Defaults to True.
            execution_policies (dict[str, bool], optional): defines supported execution language

        Raises:
            ValueError: On argument error, or if the container fails to start.
        """
        if kube_config_file is None:
            config.load_config()
        else:
            config.load_config(config_file=kube_config_file)

        self._api_client = client.CoreV1Api()

        if timeout < 1:
            raise ValueError("Timeout must be greater than or equal to 1.")
        self._timeout = timeout

        if isinstance(work_dir, str):
            work_dir = Path(work_dir)
        self._work_dir: Path = work_dir

        if container_name is None:
            container_name = "autogen-code-exec"
        self._container_name = container_name

        # Start a container from the image, read to exec commands later
        if pod_spec:
            pod = pod_spec
        else:
            if pod_name is None:
                pod_name = f"autogen-code-exec-{uuid.uuid4()}"
            if namespace is None:
                namespace_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
                if not Path(namespace_path).is_file():
                    raise ValueError("Namespace where the pod will be launched must be provided")
                with open(namespace_path, "r") as f:
                    namespace = f.read()

            pod = client.V1Pod(
                metadata=client.V1ObjectMeta(name=pod_name, namespace=namespace),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            args=["-c", "while true;do sleep 5; done"],
                            command=["/bin/sh"],
                            name=container_name,
                            image=image,
                        )
                    ],
                ),
            )

        try:
            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace
            self._pod = self._api_client.create_namespaced_pod(namespace=namespace, body=pod)
        except ApiException as e:
            raise ValueError(f"Creating pod failed: {e}")

        self._wait_for_ready()

        def cleanup() -> None:
            try:
                self._api_client.delete_namespaced_pod(pod_name, namespace)
            except ApiException:
                pass
            atexit.unregister(cleanup)

        self._cleanup = cleanup

        if stop_container:
            atexit.register(cleanup)

        self.execution_policies = self.DEFAULT_EXECUTION_POLICY.copy()
        if execution_policies is not None:
            self.execution_policies.update(execution_policies)

    def _wait_for_ready(self, stop_time: float = 0.1) -> None:
        elapsed_time = 0.0
        name = self._pod.metadata.name
        namespace = self._pod.metadata.namespace
        while True:
            sleep(stop_time)
            elapsed_time += stop_time
            if elapsed_time > self._timeout:
                raise ValueError(
                    f"pod name {name} on namespace {namespace} is not Ready after timeout {self._timeout} seconds"
                )
            try:
                pod_status = self._api_client.read_namespaced_pod_status(name, namespace)
                if pod_status.status.phase == "Running":
                    break
            except ApiException as e:
                raise ValueError(f"reading pod status failed: {e}")

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

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CommandLineCodeResult:
        """(Experimental) Execute the code blocks and return the result.

        Args:
            code_blocks (List[CodeBlock]): The code blocks to execute.

        Returns:
            CommandlineCodeResult: The result of the code execution."""

        if len(code_blocks) == 0:
            raise ValueError("No code blocks to execute.")

        outputs = []
        files = []
        last_exit_code = 0
        for code_block in code_blocks:
            lang = self.LANGUAGE_ALIASES.get(code_block.language.lower(), code_block.language.lower())
            if lang not in self.DEFAULT_EXECUTION_POLICY:
                outputs.append(f"Unsupported language {lang}\n")
                last_exit_code = 1
                break

            execute_code = self.execution_policies.get(lang, False)
            code = silence_pip(code_block.code, lang)
            if lang in ["bash", "shell", "sh"]:
                code = "\n".join(["#!/bin/bash", code])

            try:
                filename = _get_file_name_from_content(code, self._work_dir)
            except ValueError:
                outputs.append("Filename is not in the workspace")
                last_exit_code = 1
                break

            if not filename:
                extension = self.LANGUAGE_FILE_EXTENSION.get(lang, lang)
                filename = f"tmp_code_{md5(code.encode()).hexdigest()}.{extension}"

            code_path = self._work_dir / filename

            exec_script = textwrap.dedent(
                """
                if [ ! -d "{workspace}" ]; then
                  mkdir {workspace}
                fi
                cat <<EOM >{code_path}\n
                {code}
                EOM
                chmod +x {code_path}"""
            )
            exec_script = exec_script.format(workspace=str(self._work_dir), code_path=code_path, code=code)
            stream(
                self._api_client.connect_get_namespaced_pod_exec,
                self._pod.metadata.name,
                self._pod.metadata.namespace,
                command=["/bin/sh", "-c", exec_script],
                container=self._container_name,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
            )

            files.append(code_path)

            if not execute_code:
                outputs.append(f"Code saved to {str(code_path)}\n")
                continue

            resp = stream(
                self._api_client.connect_get_namespaced_pod_exec,
                self._pod.metadata.name,
                self._pod.metadata.namespace,
                command=["timeout", str(self._timeout), _cmd(lang), str(code_path)],
                container=self._container_name,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False,
            )

            stdout_messages = []
            stderr_messages = []
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stderr():
                    stderr_messages.append(resp.read_stderr())
                if resp.peek_stdout():
                    stdout_messages.append(resp.read_stdout())
            outputs.extend(stdout_messages + stderr_messages)
            exit_code = resp.returncode
            resp.close()

            if exit_code == 124:
                outputs.append("\n" + TIMEOUT_MSG)

            last_exit_code = exit_code
            if exit_code != 0:
                break

        code_file = str(files[0]) if files else None
        return CommandLineCodeResult(exit_code=last_exit_code, output="".join(outputs), code_file=code_file)

    def stop(self) -> None:
        """(Experimental) Stop the code executor."""
        self._cleanup()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.stop()
